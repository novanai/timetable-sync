from __future__ import annotations

import abc
import dataclasses
import datetime
import enum
import re
import typing

from timetable import utils

LOCATION_REGEX = re.compile(
    r"^((?P<campus>[A-Z]{3})\.)?(?P<building>VB|[A-Z][AC-FH-Z]?)(?P<floor>[BG1-9])(?P<room>[0-9\-A-Za-z ()]+)$"
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


class CategoryType(enum.Enum):
    MODULES = "525fe79b-73c3-4b5c-8186-83c652b3adcc"
    LOCATIONS = "1e042cb1-547d-41d4-ae93-a1f2c3d34538"
    PROGRAMMES_OF_STUDY = "241e4d36-60e0-49f8-b27e-99416745d98d"


class ModelBase(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        ...


@dataclasses.dataclass
class CategoryResults(ModelBase):
    categories: list[Category]
    count: int

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            [Category.from_payload(c) for c in payload["Results"]],
            payload["Count"],
        )


@dataclasses.dataclass
class Category(ModelBase):
    description: str | None
    category_type: CategoryType  # I guess this should be a UUID with extra methods for fetching it or smth
    parent_categories: list[str]
    identity: str
    name: str

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            payload["Description"],
            CategoryType(payload["CategoryTypeIdentity"]),
            payload["ParentCategoryIdentities"],
            payload["Identity"],
            payload["Name"],
        )


@dataclasses.dataclass
class CategoryTimetable(ModelBase):
    category_type: CategoryType
    category_type_name: str
    identity: str
    name: str
    events: list[Event]

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        return cls(
            payload["CategoryEvents"][0]["CategoryTypeIdentity"],
            payload["CategoryEvents"][0]["CategoryTypeName"],
            payload["CategoryEvents"][0]["Identity"],
            payload["CategoryEvents"][0]["Name"],
            [Event.from_payload(e) for e in payload["CategoryEvents"][0]["Results"]],
        )


@dataclasses.dataclass
class Event(ModelBase):
    identity: str
    start: datetime.datetime
    end: datetime.datetime
    status_identity: str
    locations: list[Location] | None
    description: str
    name: str
    event_type: str
    last_modified: datetime.datetime
    module_name: str | None
    staff_member: str | None
    weeks: list[int] | None

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

        return cls(
            payload["Identity"],
            datetime.datetime.fromisoformat(payload["StartDateTime"]),
            datetime.datetime.fromisoformat(payload["EndDateTime"]),
            payload["StatusIdentity"],
            Location.from_payloads(payload)
            if payload["Location"] is not None
            else None,
            payload["Description"],
            payload["Name"],
            payload["EventType"],
            datetime.datetime.fromisoformat(payload["LastModified"]),
            **extra_data,
        )


@dataclasses.dataclass
class Location(ModelBase):
    campus: str
    building: str
    floor: str
    room: str

    @classmethod
    def from_payload(cls, payload: dict[str, typing.Any]) -> typing.Self:
        raise NotImplementedError

    @classmethod
    def from_payloads(cls, payload: dict[str, typing.Any]) -> list[typing.Self]:
        location: str = payload["Location"]
        locations: list[str] = []

        if "&" in location:
            campus, rooms = location.split(".")
            rooms = [r.strip() for r in rooms.split("&")]
            locations.extend((f"{campus}.{room}" for room in rooms))

        elif "," in location:
            locations.extend((loc.strip() for loc in location.split(",")))
        else:
            locations = [location]

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

        # fallback
        campus, loc = location.split(".")

        return [cls(campus, "", "", loc)]

    def __str__(self) -> str:
        return f"{self.campus}.{self.building}{self.floor}{self.room}"

    def pretty_string(self, include_original: bool = False) -> str:
        return (
            f"{self.floor}.{self.room}, "
            f"{BUILDINGS[self.campus][self.building]} ({self.building}), "
            f"{CAMPUSES[self.campus]} ({self.campus})"
            + (f" ({str(self)})" if include_original else "")
        )
