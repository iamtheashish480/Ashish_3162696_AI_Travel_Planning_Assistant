"""MCP server exposing live Singapore travel tools.

This file is intentionally small: the application talks to it through the
standard MCP stdio transport instead of calling the external APIs directly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests
from mcp.server import MCPServer


mcp = MCPServer(
    "Singapore Travel Tools",
    instructions=(
        "Provides current Singapore weather forecasts and currency conversion. "
        "These values come from external services and should be treated as live data."
    ),
)

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CURRENCY_URL = "https://open.er-api.com/v6/latest"
SINGAPORE_LATITUDE = 1.3521
SINGAPORE_LONGITUDE = 103.8198
SINGAPORE_TIMEZONE = "Asia/Singapore"


def _weather_description(code: int | None) -> str:
    """Convert an Open-Meteo WMO weather code into readable text."""
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return descriptions.get(code, "Unknown conditions")


@mcp.tool()
def get_weather_forecast(start_date: str = "", days: int = 3) -> str:
    """Get a live Singapore weather forecast for 1-7 consecutive days.

    Args:
        start_date: Forecast start date in YYYY-MM-DD format. Leave blank for
            today in Singapore. A future date can be used for next-week trips.
        days: Number of forecast days, from 1 to 7.
    """
    try:
        if not 1 <= days <= 7:
            return "[MCP ERROR] 'days' must be between 1 and 7."

        singapore_today = datetime.now(ZoneInfo(SINGAPORE_TIMEZONE)).date()
        if start_date:
            try:
                start = date.fromisoformat(start_date)
            except ValueError:
                return "[MCP ERROR] start_date must use YYYY-MM-DD format."
        else:
            start = singapore_today

        if start < singapore_today:
            return "[MCP ERROR] start_date cannot be in the past."

        end = start + timedelta(days=days - 1)

        params = {
            "latitude": SINGAPORE_LATITUDE,
            "longitude": SINGAPORE_LONGITUDE,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max"
            ),
            "timezone": SINGAPORE_TIMEZONE,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }

        response = requests.get(WEATHER_URL, params=params, timeout=10)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        daily = data.get("daily", {})

        dates = daily.get("time", [])
        codes = daily.get("weather_code", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_sum", [])
        rain_probability = daily.get("precipitation_probability_max", [])

        if not dates:
            return "[MCP ERROR] Weather service returned no forecast data."

        lines = [
            "[MCP WEATHER TOOL RESULT]",
            f"Location: Singapore",
            f"Forecast period: {dates[0]} to {dates[-1]}",
            f"Retrieved at: {datetime.now(ZoneInfo(SINGAPORE_TIMEZONE)).isoformat()}",
            "Source: Open-Meteo (https://open-meteo.com/)",
            "",
        ]

        for i, forecast_date in enumerate(dates):
            code = codes[i] if i < len(codes) else None
            max_temp = max_temps[i] if i < len(max_temps) else "N/A"
            min_temp = min_temps[i] if i < len(min_temps) else "N/A"
            precipitation = rain[i] if i < len(rain) else "N/A"
            probability = rain_probability[i] if i < len(rain_probability) else "N/A"
            lines.append(
                f"{forecast_date}: {_weather_description(code)}; "
                f"min {min_temp}°C; max {max_temp}°C; "
                f"precipitation {precipitation} mm; "
                f"rain probability {probability}%"
            )

        return "\n".join(lines)

    except requests.RequestException as exc:
        return f"[MCP TOOL FAILURE] Weather service unavailable: {exc}"
    except Exception as exc:  # defensive tool boundary
        return f"[MCP TOOL FAILURE] Weather tool error: {exc}"


@mcp.tool()
def convert_currency(amount: float, from_currency: str, to_currency: str = "SGD") -> str:
    """Convert an amount using the live exchange-rate service.

    Args:
        amount: Positive amount to convert.
        from_currency: Three-letter source currency, such as INR or USD.
        to_currency: Three-letter target currency, such as SGD or INR.
    """
    try:
        if amount < 0:
            return "[MCP ERROR] amount must be zero or greater."

        source = from_currency.strip().upper()
        target = to_currency.strip().upper()

        if len(source) != 3 or len(target) != 3:
            return "[MCP ERROR] Currencies must use three-letter ISO-style codes."

        response = requests.get(f"{CURRENCY_URL}/{source}", timeout=10)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        if data.get("result") != "success":
            return "[MCP ERROR] Exchange-rate service did not return a successful result."

        rates = data.get("rates", {})
        rate = rates.get(target)
        if rate is None:
            return f"[MCP ERROR] Target currency '{target}' was not returned by the service."

        converted = amount * float(rate)
        retrieved_at = datetime.now(ZoneInfo(SINGAPORE_TIMEZONE)).isoformat()

        return (
            "[MCP CURRENCY TOOL RESULT]\n"
            f"{amount:.2f} {source} = {converted:.2f} {target}\n"
            f"Exchange rate: 1 {source} = {float(rate):.6f} {target}\n"
            f"Retrieved at: {retrieved_at}\n"
            "Source: ExchangeRate-API (https://www.exchangerate-api.com/)"
        )

    except requests.RequestException as exc:
        return f"[MCP TOOL FAILURE] Currency service unavailable: {exc}"
    except Exception as exc:  # defensive tool boundary
        return f"[MCP TOOL FAILURE] Currency tool error: {exc}"


if __name__ == "__main__":
    # MCP's default transport is stdio. Do not print to stdout while the
    # server is running because stdout carries the MCP protocol messages.
    mcp.run()
