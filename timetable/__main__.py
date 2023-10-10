import uvicorn

if __name__ == "__main__":
    uvicorn.run( # pyright: ignore[reportUnknownMemberType]
        "timetable.server:app", host="0.0.0.0", port=80,
    )
