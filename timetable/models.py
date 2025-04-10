from __future__ import annotations

import abc
import dataclasses
import datetime
import enum
import logging
import re
import typing

from timetable import utils

logger = logging.getLogger(__name__)

LOCATION_REGEX = re.compile(
    r"^((?P<campus>[A-Z]{3})\.)?(?P<building>VB|[A-Z][AC-FH-Z]?)(?P<floor>[BG1-9])(?P<room>[0-9\-A-Za-z ()]+)$"
)

# NOTE: this does not match the full inputs below (it takes only the second module and semester)
# HIS1013[2]HIS1014[2]L1/01
# HIS1013[2]HIS1014[2]L2/01

EVENT_NAME_REGEX = re.compile(
    r"(?P<modules>(?:[A-Za-z]+[0-9]+)(?:\/[A-Za-z]+[0-9]+)*)(?:[\[\(]?(?P<semester>(0|1|2|1,2|F))[\]\)]?)(?:(?P<delivery>OC|0C|ASY|AY|AS|SY|HY)\/)?(?P<activity>EX|WS|P|L|T|W|S|E|A)\d{0,2}(?:\/(?P<group>\d+))?"
)
EVENT_NAME_SUBSTITUTIONS: dict[str, str] = {
    " ": "",
    "//": "/",
    "]/": "]",
    "/]": "/",
    "[/": "]",
    "]]": "]",
    "])": "]",
    "[[": "[",
    "}": "",
}

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
        "FT": "The Polaris Building",
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


class CategoryType(enum.Enum):
    """A category type."""

    MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
    """Modules."""
    LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
    """Locations."""
    PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"
    """Programmes of Study (Courses)."""


class DisplayEnum(enum.Enum):
    """Enum with method for displaying the value in a proper format."""

    @property
    def display(self) -> str:
        """Proper format for enum value."""
        return self.name.replace("_", " ").title()


class Semester(DisplayEnum):
    """The semester."""

    ALL_YEAR = 0
    """All year (both semesters)."""
    SEMESTER_1 = 1
    """Semester 1."""
    SEMESTER_2 = 2
    """Semester 2."""


class DeliveryType(DisplayEnum):
    """Delivery type of an event."""

    ON_CAMPUS = "OC"
    """On campus."""
    ASYNCHRONOUS = "AY"
    """Asynchronous (recorded)."""
    SYNCHRONOUS = "SY"
    """Synchronous (online, live)."""
    HYBRID = "HY"
    """Hybrid."""

    @property
    def display(self) -> str:
        return DELIVERY_TYPES[self]


DELIVERY_TYPES: dict[DeliveryType, str] = {
    DeliveryType.ON_CAMPUS: "On Campus",
    DeliveryType.ASYNCHRONOUS: "Asynchronous (Recorded)",
    DeliveryType.SYNCHRONOUS: "Synchronous (Online, live)",
}


class ActivityType(DisplayEnum):
    """Activity type of an event."""

    PRACTICAL = "P"
    """Practical."""
    LECTURE = "L"
    """Lecture."""
    TUTORIAL = "T"
    """Tutorial."""
    WORKSHOP = "W"
    """Workshop."""
    SEMINAR = "S"
    """Seminar."""
    WORKSHOP_SEMINAR = "WS"
    """Workshop seminar."""
    EXAMINATION = "E"
    """Examination."""
    ASSESSMENT = "A"
    """Assessment."""


class ModelBase(abc.ABC):
    """Base model class."""

    @classmethod
    @abc.abstractmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self: ...

    @classmethod
    def from_payloads(
        cls, payloads: typing.Sequence[dict[str, typing.Any]]
    ) -> list[typing.Self]:
        return [cls.from_payload(p) for p in payloads]


@dataclasses.dataclass
class Category(ModelBase):
    """Information about a category."""

    items: list[CategoryItem]
    """The category items."""
    count: int
    """The number of items in this category."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            items=CategoryItem.from_payloads(payload["Results"]),
            count=payload["Count"],
        )


@dataclasses.dataclass
class CategoryItem(ModelBase):
    """An item belonging to a category. This could be a course, module or location."""

    description: str | None
    """- For courses, this is the full title of the course.
    - For modules, this is either the full title of the module or `None`.
    - For locations, this is a brief description of the location.
    In the cases of description being `None`, `CategoryItem.name` should be used.
    ### Examples
    - Courses: `"BSc in Computer Science"`
    - Modules: `"Computer Programming I"` / `None`
    - Locations: `"Tiered Lecture Theatre"`
    """
    category_type: CategoryType
    """The type of category this item belongs to."""
    parent_categories: list[str]
    """Unique identities of the parent category(ies)."""
    identity: str
    """Unique identity of this category item."""
    name: str
    """- For courses, this is the course code.
    - For modules, this is the full module name, including the code, semester and full title.
    - For locations, this is the location's code, which can be parsed by `Location.from_str`
    ### Examples:
    - Courses: `"COMSCI1"`
    - Modules: `"CSC1003[1] Computer Programming I"`
    - Locations: `"GLA.C117 & C122"`
    """
    code: str
    """The course, module or location code(s).
    If this is for a location, it may contain multiple codes separated by a space.
    ### Examples:
    - Courses: `"COMSCI1"`
    - Modules: `"CSC1003[1]"`
    - Locations: `"GLA.C117 GLA.C122"`
    """

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        cat_type = CategoryType(payload["CategoryTypeIdentity"])
        name: str = payload["Name"]

        if cat_type is CategoryType.LOCATIONS:
            locations = Location.from_str(name)
            code = " ".join([str(loc) for loc in locations])
        else:
            code = name.split(" ")[0]

        return cls(
            description=payload["Description"].strip() or None,
            category_type=cat_type,
            parent_categories=payload["ParentCategoryIdentities"],
            identity=payload["Identity"],
            name=name,
            code=code.strip(),
        )


@dataclasses.dataclass
class CategoryItemTimetable(ModelBase):
    """A category item's timetable."""

    category_type: CategoryType
    """The type of category this timetable is for."""
    identity: str
    """The identity of the category item this timetable is for."""
    name: str
    """- For courses, this is the course code.
    - For modules, this is the full module name, including the code, semester and full title.
    - For locations, this is the location code.
    ### Examples
    - Courses: `"COMSCI1"`
    - Modules: `"CSC1003[1] Computer Programming I"`
    - Locations: `"GLA.L129"`
    """
    events: list[Event]
    """Events on this timetable."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            category_type=payload["CategoryTypeIdentity"],
            identity=payload["Identity"],
            name=payload["Name"],
            events=Event.from_payloads(payload["Results"]),
        )


@dataclasses.dataclass
class Event(ModelBase):
    """A timetabled event."""

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
    - T3 (Tutorial 3) all share the same identity (but a different identity to L1)
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
    
    If this is in the form `MODULE[SEMESTER]EVENT/ACTIVITY/GROUP` (e.g. `"CSC1003[1]OC/L1/01"`),
    then `Event.parsed_name_data` will be available.
    """
    event_type: str
    """The activity type, almost always `"On Campus"`, `"Synchronous (Online, live)"`,
    `"Asynchronous (Recorded)"` or `"Booking"`.
    """
    last_modified: datetime.datetime
    """The last time this event was modified."""
    module_name: str | None
    """The full module name.
    ### Example
    CSC1003[1] Computer Programming I
    """
    staff_member: str | None
    """The event's staff member's name.
    ### Example
    Blott S
    """
    weeks: list[int] | None
    """List of week numbers this event takes place on."""
    group_name: str | None
    """The group name, if parsed from either the event name or description."""
    parsed_name_data: list[ParsedNameData]
    """Data parsed from the event name into proper formats. May be an empty list (if parsing
    was unsuccessful).
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
            for value in (name, description):
                if grp in value and (index := value.index(grp) + len(grp)) < len(value):
                    group_name = value[index].upper()
                    break

        return cls(
            identity=payload["Identity"],
            start=datetime.datetime.fromisoformat(payload["StartDateTime"]),
            end=datetime.datetime.fromisoformat(payload["EndDateTime"]),
            status_identity=payload["StatusIdentity"],
            locations=Location.from_str(payload["Location"])
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
            parsed_name_data=ParsedNameData.from_str(payload["Name"]),
        )


@dataclasses.dataclass
class ParsedNameData(ModelBase):
    """Data parsed from the event name into proper formats."""

    module_codes: list[str]
    """A list of module codes this event is for.
    ### Example
    `["PS114", "PS114A"]`
    """
    semester: Semester
    """The semester this event takes place in."""
    delivery_type: DeliveryType | None
    """The delivery type of this event. May be `None`."""
    activity_type: ActivityType
    """The activity type of this event."""
    group_number: int | None
    """The group this event is for. May be `None`."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        raise NotImplementedError

    @classmethod
    def from_str(cls, data: str) -> list[ParsedNameData]:
        # Ignore anything without a `/` as this guarantees it
        # won't match the regex and speeds up processing
        if "/" not in data:
            return []

        # Some error correction
        data = data.upper()
        for original, substitution in EVENT_NAME_SUBSTITUTIONS.items():
            data = data.replace(original, substitution)

        matches: list[ParsedNameData] = []

        for match in EVENT_NAME_REGEX.finditer(data):
            modules = [
                module for module in match.group("modules").split("/") if module.strip()
            ]

            sem = match.group("semester")
            if sem == "1,2":
                sem = "0"
            elif sem == "F":
                sem = "0"
            semester = Semester(int(sem))

            dt = match.group("delivery")

            if dt is not None:
                if dt == "0C":
                    dt = "OC"
                elif dt == "AS":
                    dt = "AY"
                elif dt == "ASY":
                    dt = "AY"
                delivery_type = DeliveryType(dt)
            else:
                delivery_type = None

            at = match.group("activity")
            if at == "EX":
                at = "E"
            activity_type = ActivityType(at)

            group = int(g) if (g := match.group("group")) else None

            matches.append(
                cls(
                    module_codes=modules,
                    semester=semester,
                    delivery_type=delivery_type,
                    activity_type=activity_type,
                    group_number=group,
                )
            )

        if not matches:
            logger.warning(f"Failed to parse: {data}")

        return matches


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
    original: str | None = None
    """The original location code. If `None`, the location was parsed correctly."""

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        raise NotImplementedError

    @classmethod
    def from_str(cls, location: str) -> list[Location]:
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

                final_locations.append(
                    cls(campus=campus, building=building, floor=floor, room=room)
                )

        if final_locations:
            return final_locations

        return [cls(campus="", building="", floor="", room="", original=location)]

    def __str__(self) -> str:
        return f"{self.campus}.{self.building}{self.floor}{self.room}"

    def pretty_string(self, include_original: bool = False) -> str:
        building_name = BUILDINGS[self.campus].get(self.building, "[unknown]")
        return (
            f"{self.floor}.{self.room}, "
            f"{building_name} ({self.building}), "
            f"{CAMPUSES[self.campus]} ({self.campus})"
            + (f", ({str(self)})" if include_original else "")
        )


class ResponseFormat(enum.Enum):
    """The response format."""

    ICAL = "ical"
    """iCalendar."""
    JSON = "json"
    """JSON."""
    UNKNOWN = "unknown"
    """Unknown."""

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


@dataclasses.dataclass
class APIError:
    """API error response."""

    status: int
    """HTTP status code."""
    message: str
    """Error message."""


@dataclasses.dataclass
class InvalidCodeError(Exception):
    """Invalid code error."""

    code: str
    """The offending code."""
