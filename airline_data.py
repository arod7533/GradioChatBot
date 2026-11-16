"""Fictional airline fixtures served from a read-only SQLite memory database."""

import json
import sqlite3
from datetime import date as calendar_date
from threading import Lock
from typing import Any

FLIGHTS = (
    {
        "flight_number": "AST 218",
        "date": "2026-12-05",
        "origin": "SFO",
        "destination": "JFK",
        "departure": "08:15",
        "arrival": "16:45",
        "price_usd": 289,
        "fare_class": "Economy",
        "status": "Scheduled",
    },
    {
        "flight_number": "AST 418",
        "date": "2026-12-05",
        "origin": "SFO",
        "destination": "JFK",
        "departure": "14:05",
        "arrival": "22:30",
        "price_usd": 259,
        "fare_class": "Economy",
        "status": "Scheduled",
    },
    {
        "flight_number": "AST 219",
        "date": "2026-12-06",
        "origin": "JFK",
        "destination": "SFO",
        "departure": "09:30",
        "arrival": "12:55",
        "price_usd": 269,
        "fare_class": "Economy",
        "status": "Scheduled",
    },
    {
        "flight_number": "AST 704",
        "date": "2026-12-05",
        "origin": "LAX",
        "destination": "SEA",
        "departure": "11:20",
        "arrival": "14:10",
        "price_usd": 149,
        "fare_class": "Economy",
        "status": "Scheduled",
    },
)

BOOKINGS = {
    "AX7K2Q": {
        "reference": "AX7K2Q",
        "passenger": "Jordan Lee",
        "flight_number": "AST 218",
        "date": "2026-12-05",
        "seat": "14A",
        "fare_class": "Economy",
        "status": "Confirmed",
    }
}

POLICIES = {
    "economy": {
        "fare_class": "Economy",
        "carry_on": "One bag up to 22 x 14 x 9 in, plus one personal item.",
        "checked_bag": "$35 for the first checked bag.",
    },
    "flex": {
        "fare_class": "Flex",
        "carry_on": "One bag up to 22 x 14 x 9 in, plus one personal item.",
        "checked_bag": "One checked bag included.",
    },
    "business": {
        "fare_class": "Business",
        "carry_on": "One bag up to 22 x 14 x 9 in, plus one personal item.",
        "checked_bag": "Two checked bags included.",
    },
}

DB_LOCK = Lock()
DB = sqlite3.connect(":memory:", check_same_thread=False)
DB.row_factory = sqlite3.Row
DB.executescript(
    """
    CREATE TABLE flights (
        flight_number TEXT PRIMARY KEY, date TEXT, origin TEXT, destination TEXT,
        departure TEXT, arrival TEXT, price_usd INTEGER, fare_class TEXT, status TEXT
    );
    CREATE TABLE bookings (
        reference TEXT PRIMARY KEY, passenger TEXT, flight_number TEXT,
        date TEXT, seat TEXT, fare_class TEXT, status TEXT
    );
    CREATE TABLE policies (
        fare_class TEXT PRIMARY KEY, carry_on TEXT, checked_bag TEXT
    );
    """
)
DB.executemany(
    "INSERT INTO flights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [tuple(flight.values()) for flight in FLIGHTS],
)
DB.executemany(
    "INSERT INTO bookings VALUES (?, ?, ?, ?, ?, ?, ?)",
    [tuple(booking.values()) for booking in BOOKINGS.values()],
)
DB.executemany(
    "INSERT INTO policies VALUES (?, ?, ?)",
    [tuple(policy.values()) for policy in POLICIES.values()],
)
DB.commit()
DB.execute("PRAGMA query_only = ON")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Find fictional Astra Air flights by origin, destination, and ISO departure date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Three-letter airport code, e.g. SFO",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Three-letter airport code, e.g. JFK",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                },
                "required": ["origin", "destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_status",
            "description": "Get the sample schedule status of a fictional flight number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {"type": "string", "description": "e.g. AST 218"}
                },
                "required": ["flight_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_booking",
            "description": "Find a fictional reservation using its six-character reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {"type": "string", "description": "e.g. AX7K2Q"}
                },
                "required": ["reference"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_baggage_policy",
            "description": "Get fictional carry-on and checked-bag rules for Economy, Flex, or Business.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fare_class": {
                        "type": "string",
                        "description": "Economy, Flex, or Business",
                    }
                },
                "required": ["fare_class"],
            },
        },
    },
]


def search_flights(origin: str, destination: str, date: str) -> dict[str, Any]:
    """Search the in-memory timetable with parameterized SQL."""
    try:
        calendar_date.fromisoformat(date)
    except ValueError:
        return {"error": "Use an ISO date in YYYY-MM-DD format."}
    origin, destination = origin.strip().upper(), destination.strip().upper()
    with DB_LOCK:
        matches = [
            dict(row)
            for row in DB.execute(
                """
                SELECT * FROM flights
                WHERE origin = ? AND destination = ? AND date = ?
                ORDER BY departure
                """,
                (origin, destination, date),
            )
        ]
    return {"flights": matches, "count": len(matches), "currency": "USD"}


def get_flight_status(flight_number: str) -> dict[str, Any]:
    """Return a sample status, not real-time operational data."""
    number = flight_number.upper().replace(" ", "")
    with DB_LOCK:
        row = DB.execute(
            "SELECT flight_number, date, status FROM flights "
            "WHERE REPLACE(flight_number, ' ', '') = ?",
            (number,),
        ).fetchone()
    if row:
        return {**dict(row), "note": "Fictional schedule; not live flight tracking."}
    return {"error": "Flight not found in the demo timetable."}


def lookup_booking(reference: str) -> dict[str, Any]:
    """Look up a fictional booking without changing any data."""
    with DB_LOCK:
        row = DB.execute(
            "SELECT * FROM bookings WHERE reference = ?", (reference.strip().upper(),)
        ).fetchone()
    return dict(row) if row else {"error": "Booking reference not found."}


def get_baggage_policy(fare_class: str) -> dict[str, Any]:
    """Return the example baggage policy for the given fare class."""
    with DB_LOCK:
        row = DB.execute(
            "SELECT * FROM policies WHERE LOWER(fare_class) = ?",
            (fare_class.strip().lower(),),
        ).fetchone()
    return (
        dict(row)
        if row
        else {"error": "Fare class not found. Try Economy, Flex, or Business."}
    )


FUNCTIONS = {
    "search_flights": search_flights,
    "get_flight_status": get_flight_status,
    "lookup_booking": lookup_booking,
    "get_baggage_policy": get_baggage_policy,
}


def run_tool(name: str, arguments: Any) -> dict[str, Any]:
    """Execute only registered read-only functions with validated arguments."""
    function = FUNCTIONS.get(name)
    if function is None:
        return {"error": "Unknown tool."}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return {"error": "Invalid tool arguments."}
    if not isinstance(arguments, dict):
        return {"error": "Invalid tool arguments."}
    try:
        return function(**arguments)
    except (TypeError, AttributeError, ValueError):
        return {"error": "Invalid tool arguments."}
