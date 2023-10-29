from __future__ import annotations

import abc
import dataclasses
import datetime
import enum
import re
import typing

from timetable import utils, logger

LOCATION_REGEX = re.compile(
    r"^((?P<campus>[A-Z]{3})\.)?(?P<building>VB|[A-Z][AC-FH-Z]?)(?P<floor>[BG1-9])(?P<room>[0-9\-A-Za-z ()]+)$"
)
EVENT_NAME_REGEX = re.compile(
    r"^(?P<courses>([A-Za-z0-9]+\/?)+)(\[|\()?(?P<semester>[0-2])(\]|\))?(?P<delivery>OC|AY|SY)\/(?P<activity>P|L|T|W|S)[0-9]\/(?P<group>[0-9]+).*$"
)

CAMPUSES = {"AHC": "All Hallows", "GLA": "Glasnevin", "SPC": "St Patrick's"}

BUILDINGS = {
    "GLA": {
        "A": "Albert College",
        "B": "Invent Building",
        "C": "Henry Grattan Building",
        "CA": "Henry Grattan Extension",
        "D": "BEA Orpen Building",
        "E": "Estates Office",
        "F": "Multi-Storey Car Park",
        "G": "NICB Building",
        "GA": "NRF Building",
        "H": "Nursing Building",
        "J": "Hamilton Building",
        "KA": "U Building / Student Centre",
        "L": "McNulty Building",
        "M": "Interfaith Centre",
        "N": "Marconi Building",
        "P": "Pavilion",
        "PR": "Restaurant",
        "Q": "Business School",
        "QA": "MacCormac Reception",
        "R": "Creche",
        "S": "Stokes Building",
        "SA": "Stokes Annex",
        "T": "Terence Larkin Theatre",
        "U": "Accommodation & Sports Club",
        "V1": "Larkfield Residences",
        "V2": "Hampstead Residences",
        "VA": "Postgraduate Residences A",
        "VB": "Postgraduate Residences B",
        "W": "College Park Residences",
        "X": "Lonsdale Building",
        "Y": "O'Reilly Library",
        "Z": "The Helix",
    },
    "SPC": {
        "A": "Block A",
        "B": "Block B",
        "C": "Block C",
        "D": "Block D",
        "E": "Block E",
        "F": "Block F",
        "G": "Block G",
        "S": "Block S / Sports Hall",
    },
    "AHC": {
        "C": "Chapel",
        "OD": "O'Donnell House",
        "P": "Purcell House",
        "S": "Senior House",
    },
}

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class CategoryType(enum.Enum):
    MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
    LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
    PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"


class DisplayEnum(enum.Enum):
    def display(self) -> str:
        return self.name.replace("_", " ").title()


class Semester(DisplayEnum):
    ALL_YEAR = 0
    SEMESTER_1 = 1
    SEMESTER_2 = 2


class DeliveryType(DisplayEnum):
    ON_CAMPUS = "OC"
    ASYNCHRONOUS = "AY"
    SYNCHRONOUS = "SY"

    def display(self) -> str:
        return DELIVERY_TYPES[self]


DELIVERY_TYPES: dict[DeliveryType, str] = {
    DeliveryType.ON_CAMPUS: "On Campus",
    DeliveryType.ASYNCHRONOUS: "Asynchronous (Recorded)",
    DeliveryType.SYNCHRONOUS: "Synchronous (Online, live)",
}


class ActivityType(DisplayEnum):
    PRACTICAL = "P"
    LECTURE = "L"
    TUTORIAL = "T"
    WORKSHOP = "W"
    SEMINAR = "S"


class ModelBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        ...


@dataclasses.dataclass
class Category(ModelBase):
    """Information about a category."""

    categories: list[CategoryItem]
    """All the items of this category."""
    count: int
    """The number of items in this category."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            [CategoryItem.from_payload(c) for c in payload["Results"]],
            payload["Count"],
        )


@dataclasses.dataclass
class CategoryItem(ModelBase):
    """An item belonging to a category. This could be a course or module."""

    description: str | None
    """- For courses, this is the full title of the course.
    - For modules, this is either the full title of the module or null.
    In the cases of it being null, `CategoryItem.name` should be used.
    ### Examples
    - Courses: `"BSc in Computer Science"`
    - Modules: `"Computing Programming I"` / `None`
    """
    category_type: CategoryType
    """The type of the category this item belongs to."""
    parent_categories: list[str]
    """Unique identities of the parent category(ies)."""
    identity: str
    """Unique identity of this category item."""
    name: str
    """- For courses, this is the course code.
    - For modules, this is the full module name, including the code, semester and full title.
    ###
    - Courses: `"COMSCI1"`
    - Modules: `"CA116[1] Computing Programming I"`
    """
    code: str
    """The course/module code (including the semester number for modules).
    ### Examples:
    - Courses: `"COMSCI1"`
    - Modules: `"CA116[1]"`
    """

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        cat_type = CategoryType(payload["CategoryTypeIdentity"])
        name: str = payload["Name"]

        if cat_type is CategoryType.MODULES:
            code = name.split(" ")[0]
        else:
            code = name

        return cls(
            payload["Description"].strip() or None,
            cat_type,
            payload["ParentCategoryIdentities"],
            payload["Identity"],
            name,
            code,
        )


@dataclasses.dataclass
class CategoryItemTimetable(ModelBase):
    category_type: CategoryType
    """The type of category this timetable is for."""
    identity: str
    """The identity of the category item this timetable is for."""
    name: str
    """- For courses, this is the course code.
    - For modules, this is the full module name, including the code, semester and full title.
    ### Examples
    - Courses: `"COMSCI1"`
    - Modules: `"CA116[1] Computing Programming I"`
    """
    events: list[Event]
    """List of events on this timetable."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            payload["CategoryTypeIdentity"],
            payload["Identity"],
            payload["Name"],
            [Event.from_payload(e) for e in payload["Results"]],
        )


@dataclasses.dataclass
class Event(ModelBase):
    identity: str
    """Unique identity of the event."""
    start: datetime.datetime
    """Start time of the event."""
    end: datetime.datetime
    """End time of the event."""
    status_identity: str
    """This appears to be an identity shared between events of the same activity type and number.
    ### Examples
    - L1 (Lecture 1) all share the same identity
    - T3 (Tutorial 3) all share the same identity (but a different one to L1)
    """
    locations: list[Location] | None
    """A list of locations for this event, or `None` if there are no locations
    (e.g. for asynchronous events).
    """
    description: str | None
    """A description of the event. This could be anything from the activity type
    (e.g. `"Lecture"`) to a brief description of the event (e.g. `"Introduction to Computing"`)
    and should therefore not be relied on to provide consistent information.
    """
    name: str
    """The name of the event.
    
    If this is in the form `MODULE[SEMESTER]EVENT/ACTIVITY/GROUP` (e.g. `"CA116[1]OC/L1/01"`),
    then `parsed_name_data` will not be `None`.
    """
    event_type: str
    """The activity type, almost always `"On Campus"`, `"Synchronous (Online, live)"`
    or `"Asynchronous (Recorded)"`.
    """
    last_modified: datetime.datetime
    """The last time this event was modified."""
    module_name: str | None
    """The full module name.
    ### Example
    CA116[1] Computing Programming I
    """
    staff_member: str | None
    """The event's staff member's name.
    ### Example
    Blott S
    """
    weeks: list[int] | None
    """List of week numbers this event takes place on."""
    group_name: str | None
    """The group name, parsed from either the event name or description."""
    parsed_name_data: ParsedNameData | None
    """Data parsed from the event name into proper formats.
    Only available for module and event timetables, if parsed correctly.
    """

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        extra_data: dict[str, typing.Any] = {
            "module_name": None,
            "staff_member": None,
            "weeks": None,
        }

        for item in payload["ExtraProperties"]:
            rank = item["Rank"]
            if rank == 1:
                extra_data["module_name"] = item["Value"]
            elif rank == 2:
                extra_data["staff_member"] = item["Value"]
            elif rank == 3:
                extra_data["weeks"] = utils.parse_weeks(item["Value"])

        name: str = payload["Name"].lower().replace(" ", "")
        description: str = payload["Description"].lower().replace(" ", "")
        group_name: str | None = None
        for grp in ("group", "grp"):
            for value in name, description:
                if grp in value:
                    group_name = value[value.index(grp) + len(grp)].upper()
                    break

        return cls(
            identity=payload["Identity"],
            start=datetime.datetime.fromisoformat(payload["StartDateTime"]),
            end=datetime.datetime.fromisoformat(payload["EndDateTime"]),
            status_identity=payload["StatusIdentity"],
            locations=Location.from_payloads(payload)
            if payload["Location"] is not None
            else None,
            description=payload["Description"].strip() or None,
            name=payload["Name"],
            event_type=payload["EventType"],
            last_modified=datetime.datetime.fromisoformat(payload["LastModified"]),
            module_name=extra_data["module_name"],
            staff_member=extra_data["staff_member"],
            weeks=extra_data["weeks"],
            group_name=group_name,
            parsed_name_data=ParsedNameData.from_payload(payload["Name"]),
        )


@dataclasses.dataclass
class ParsedNameData:
    """Data parsed from the event name into proper formats."""

    course_codes: list[str]
    """A list of course codes this event is for.
    ### Example
    `["PS114", "PS114A"]`
    """
    semester: Semester
    """The semester this event takes place in."""
    delivery_type: DeliveryType
    """The delivery type of this event."""
    activity_type: ActivityType
    """The activity type of this event."""
    group_number: int
    """The group this event is for."""

    @classmethod
    def from_payload(cls, data: str) -> typing.Self | None:
        if match := EVENT_NAME_REGEX.match(data):
            courses = match.group("courses")
            semester = Semester(int(match.group("semester")))
            delivery_type = DeliveryType(match.group("delivery"))
            activity_type = ActivityType(match.group("activity"))
            # TODO: group is actually optional, I think
            group = int(match.group("group"))

            return cls(
                [course for course in courses.split("/") if course.strip()],
                semester,
                delivery_type,
                activity_type,
                group,
            )
        else:
            logger.warning(f"Failed to parse name: '{data}'")


@dataclasses.dataclass
class Location(ModelBase):
    """A location."""

    campus: str
    """The campus code.
    ### Allowed Values
    `"GLA"`, `"SPC"`, `"AHC"`
    """
    building: str
    """The building code.
    ### Examples
    `"L"`, `"SA"` 
    """
    floor: str
    """The floor code.
    ### Allowed Values
    `"B"` - Basement, `"G"` - Ground Floor, `number > 0` - Floor Number
    """
    room: str
    """The room code. Not guaranteed to be just a number."""
    error: bool = False
    """`True` if this location was not parsed correctly, otherwise `False`"""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        raise NotImplementedError

    @classmethod
    def from_payloads(cls, payload: dict[str, typing.Any]) -> list[typing.Self]:
        location: str = payload["Location"]
        locations: list[str] = []

        for loc in location.split(","):
            loc = loc.strip()
            if "&" in loc:
                campus, rooms = loc.split(".")
                rooms = [r.strip() for r in rooms.split("&")]
                locations.extend((f"{campus}.{room}" for room in rooms))
            else:
                locations.append(loc)

        final_locations: list[Location] = []
        for loc in locations:
            if match := LOCATION_REGEX.match(loc):
                campus = match.group("campus")
                building = match.group("building")
                floor = match.group("floor")
                room = match.group("room")

                final_locations.append(cls(campus, building, floor, room))

        if final_locations:
            return final_locations

        logger.warning(f"Failed to parse location: '{location}'")

        # fallback
        campus, loc = location.split(".")

        return [cls(campus, "", "", loc, True)]

    def __str__(self) -> str:
        return f"{self.campus}.{self.building}{self.floor}{self.room}"

    def pretty_string(self, include_original: bool = False) -> str:
        return (
            f"{self.floor}.{self.room}, "
            f"{BUILDINGS[self.campus][self.building]} ({self.building}), "
            f"{CAMPUSES[self.campus]} ({self.campus})"
            + (f" ({str(self)})" if include_original else "")
        )


class ResponseFormat(enum.Enum):
    ICAL = "ical"
    JSON = "json"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, format: str | None) -> typing.Self:
        format = format.lower() if format else "ical"
        try:
            return cls(format)
        except ValueError:
            return cls("unknown")

    @property
    def content_type(self) -> str:
        return RESPONSE_FORMATS[self]


RESPONSE_FORMATS: dict[ResponseFormat, str] = {
    ResponseFormat.ICAL: "text/calendar",
    ResponseFormat.JSON: "application/json",
}
