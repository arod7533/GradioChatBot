"""Deterministic checks for the fictional, read-only SQLite tools."""

import sqlite3
import unittest

from airline_data import (
    BOOKINGS,
    DB,
    FLIGHTS,
    get_baggage_policy,
    get_flight_status,
    lookup_booking,
    run_tool,
    search_flights,
)


class AirlineDataTests(unittest.TestCase):
    def test_search_normalizes_airports_and_returns_matching_date(self):
        result = search_flights("sfo", " jfk ", "2026-12-05")
        self.assertEqual(result["count"], 2)
        self.assertEqual(
            {flight["flight_number"] for flight in result["flights"]},
            {"AST 218", "AST 418"},
        )

    def test_search_has_no_fabricated_results(self):
        self.assertEqual(search_flights("BOS", "JFK", "2026-12-05")["flights"], [])
        self.assertIn("error", search_flights("SFO", "JFK", "tomorrow"))

    def test_flight_status_is_sample_not_live(self):
        result = get_flight_status("ast218")
        self.assertEqual(result["status"], "Scheduled")
        self.assertIn("not live", result["note"])
        self.assertIn("error", get_flight_status("AST 999"))

    def test_booking_lookup_and_policy(self):
        self.assertEqual(lookup_booking(" ax7k2q ")["seat"], "14A")
        self.assertIn("error", lookup_booking("UNKNOWN"))
        self.assertIn("$35", get_baggage_policy(" economy ")["checked_bag"])
        self.assertIn("error", get_baggage_policy("First"))

    def test_tool_allowlist_rejects_bad_arguments(self):
        self.assertEqual(
            run_tool("delete_booking", {"reference": "AX7K2Q"}),
            {"error": "Unknown tool."},
        )
        self.assertIn("error", run_tool("search_flights", '{"origin":'))
        self.assertIn("error", run_tool("search_flights", {"origin": "SFO"}))
        self.assertIn("error", run_tool("search_flights", []))

    def test_tools_do_not_mutate_fixtures(self):
        original = lookup_booking("AX7K2Q")
        original["seat"] = "1A"
        search_flights("SFO", "JFK", "2026-12-05")["flights"][0]["price_usd"] = 1
        self.assertEqual(BOOKINGS["AX7K2Q"]["seat"], "14A")
        self.assertEqual(FLIGHTS[0]["price_usd"], 289)

    def test_database_is_read_only_and_queries_are_parameterized(self):
        self.assertEqual(
            search_flights("SFO' OR 1=1 --", "JFK", "2026-12-05")["count"], 0
        )
        self.assertIn("error", lookup_booking("AX7K2Q' OR 1=1 --"))
        with self.assertRaises(sqlite3.OperationalError):
            DB.execute("UPDATE bookings SET seat = '1A'")


if __name__ == "__main__":
    unittest.main()
