import datetime

from blacksheep.server.openapi.common import (
    ContentInfo,
    EndpointDocs,
    ParameterInfo,
    ResponseInfo,
)

from timetable import models

API = EndpointDocs(
    summary="Generate a timetable.",
    description="One of 'course', 'courses' or 'modules' must be provided, but not both. All other parameters are optional.",
    parameters={
        "course": ParameterInfo(
            "The course to generate a timetable for.",
            str,
            required=False,
            example="COMSCI1",
        ),
        "courses": ParameterInfo(
            "The course(s) to generate a timetable for.",
            str,
            required=False,
            example="COMSCI1,COMSCI2"
        ),
        "modules": ParameterInfo(
            "The module(s) to generate a timetable for.",
            str,
            required=False,
            example="CA103,CA116,MS134",
        ),
        "format": ParameterInfo(
            "The response format.\n\nAllowed values: 'ical' or 'json'.\nDefault: 'ical'.",
            str,
            required=False,
            example="json",
        ),
        "display": ParameterInfo(
            "Whether or not to include additional display info",
            bool,
            required=False,
            example="true",
        ),
        "start": ParameterInfo(
            "Only get timetable events later than this datetime.",
            str,
            required=False,
            example="2023-10-31T13:00:00",
        ),
        "end": ParameterInfo(
            "Only get timetable events earlier than this datetime.",
            str,
            required=False,
            example="2024-04-23T10:00:00",
        ),
    },
    responses={
        200: ResponseInfo(
            (
                "Successfully generated a timetable. However, it is not guaranteed to actually contain any events.\n\n"
                "If format was 'json', response will be in json format. Otherwise if format was 'ical' or not specified, "
                "response will be in plain text."
            ),
            content=[
                ContentInfo(
                    str,
                    examples=[
                        """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//nova@redbrick.dcu.ie//TimetableSync//EN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:CA116 Computing Programming I (Lecture)
DTSTART:20230925T090000Z
DTEND:20230925T110000Z
DTSTAMP:20231030T154328Z
UID:aac10915-54ec-4128-996e-3e371dd39d42
CLASS:PUBLIC
DESCRIPTION:Lecture\\, On Campus
LAST-MODIFIED:20231012T112440Z
LOCATION:HG23 (Nursing Building\\, Glasnevin)
END:VEVENT
END:VCALENDAR
"""
                    ],
                    content_type="text/plain",
                ),
                # TODO: update this to include display properties if available
                ContentInfo(
                    list[models.Event],
                    examples=[
                        [
                            models.Event(
                                identity="30658267-d87b-4dfc-9086-ae594bf1de1c",
                                start=datetime.datetime.fromisoformat(
                                    "2023-09-28T10:00:00+00:00"
                                ),
                                end=datetime.datetime.fromisoformat(
                                    "2023-09-28T11:00:00+00:00"
                                ),
                                status_identity="119e2af6-701c-4442-8230-a5c5020f308e",
                                locations=[
                                    models.Location(
                                        campus="GLA",
                                        building="Q",
                                        floor="G",
                                        room="15",
                                        error=False,
                                    ),
                                ],
                                description="Lecture",
                                name="CA116[1]OC/L1/01",
                                event_type="On Campus",
                                last_modified=datetime.datetime.fromisoformat(
                                    "2023-06-29T09:41:17.367634+00:00"
                                ),
                                module_name="CA116[1] Computing Programming I",
                                staff_member="Blott S",
                                weeks=[3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                                group_name=None,
                                parsed_name_data=[
                                    models.ParsedNameData(
                                        module_codes=["CA116"],
                                        semester=models.Semester.SEMESTER_1,
                                        delivery_type=models.DeliveryType.ON_CAMPUS,
                                        activity_type=models.ActivityType.LECTURE,
                                        group_number=1,
                                    )
                                ],
                            )
                        ],
                    ],
                ),
            ],
        ),
        400: ResponseInfo(
            description=(
                "Bad Request.\n\nIf format was 'json', response will be in json format. Otherwise, response will be in plain text."
            ),
            content=[
                ContentInfo(
                    type=str,
                    examples=["Cannot provide both course and modules."],
                    content_type="text/plain",
                ),
                ContentInfo(
                    type=models.APIError,
                    examples=[
                        models.APIError(400, "Cannot provide both course and modules.")
                    ],
                    content_type="application/json",
                ),
            ],
        ),
    },
)
