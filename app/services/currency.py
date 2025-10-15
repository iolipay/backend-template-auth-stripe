import httpx
from datetime import datetime, date
from typing import Dict, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class CurrencyService:
    """Service for fetching and caching currency exchange rates from National Bank of Georgia"""

    NBG_API_URL = "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/"
    CACHE_TTL = 3600  # Cache rates for 1 hour

    def __init__(self):
        self._cache: Dict[str, Dict[str, float]] = {}  # {date: {currency: rate}}
        self._cache_timestamps: Dict[str, datetime] = {}  # {date: timestamp}

    async def get_exchange_rate(self, currency: str, target_date: Optional[date] = None) -> float:
        """
        Get exchange rate for a currency to GEL.

        Args:
            currency: Currency code (e.g., "USD", "EUR")
            target_date: Date for the exchange rate (default: today)

        Returns:
            Exchange rate (e.g., 2.7111 means 1 USD = 2.7111 GEL)

        Raises:
            HTTPException: If currency is not found or API error occurs
        """
        # GEL to GEL is always 1.0
        if currency.upper() == "GEL":
            return 1.0

        # Use today if no date specified
        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime("%Y-%m-%d")

        # Check cache first
        if self._is_cache_valid(date_str):
            cached_rates = self._cache.get(date_str, {})
            if currency.upper() in cached_rates:
                logger.info(f"Cache hit for {currency} on {date_str}")
                return cached_rates[currency.upper()]

        # Fetch from API
        logger.info(f"Fetching exchange rates from NBG API for {date_str}")
        rates = await self._fetch_rates_from_api(target_date)

        # Cache the rates
        self._cache[date_str] = rates
        self._cache_timestamps[date_str] = datetime.now()

        # Get the requested currency
        if currency.upper() not in rates:
            available_currencies = ", ".join(sorted(rates.keys()))
            raise HTTPException(
                status_code=400,
                detail=f"Currency {currency.upper()} not found. Available currencies: {available_currencies}"
            )

        return rates[currency.upper()]

    async def convert_to_gel(self, amount: float, currency: str, target_date: Optional[date] = None) -> tuple[float, float]:
        """
        Convert an amount from any currency to GEL.

        Args:
            amount: Amount in original currency
            currency: Currency code (e.g., "USD", "EUR")
            target_date: Date for the exchange rate (default: today)

        Returns:
            Tuple of (amount_in_gel, exchange_rate)
        """
        rate = await self.get_exchange_rate(currency, target_date)
        amount_gel = round(amount * rate, 2)
        return amount_gel, rate

    async def _fetch_rates_from_api(self, target_date: date) -> Dict[str, float]:
        """
        Fetch exchange rates from NBG API.

        Args:
            target_date: Date for the exchange rates

        Returns:
            Dictionary mapping currency codes to exchange rates

        Raises:
            HTTPException: If API request fails
        """
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{self.NBG_API_URL}?date={date_str}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # Parse the response - NBG API returns: [{"date": "...", "currencies": [...]}]
            rates = {}

            # Extract currencies from the NBG API response format
            if isinstance(data, list) and len(data) > 0:
                currencies = data[0].get("currencies", [])
            elif isinstance(data, dict):
                currencies = data.get("currencies", [])
            else:
                currencies = []

            if not currencies:
                logger.warning(f"No currencies found in NBG API response for {date_str}")
                raise HTTPException(
                    status_code=400,
                    detail=f"No exchange rates available for {date_str}. The date might be a weekend or holiday."
                )

            for currency_data in currencies:
                code = currency_data.get("code")
                rate = currency_data.get("rate")
                quantity = currency_data.get("quantity", 1)

                if code and rate:
                    # Adjust rate based on quantity (some currencies are quoted per 100 units)
                    adjusted_rate = rate / quantity if quantity > 0 else rate
                    rates[code] = adjusted_rate

            logger.info(f"Fetched {len(rates)} exchange rates for {date_str}")
            return rates

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching NBG rates: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch exchange rates from NBG API: {str(e)}"
            )
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBG rates: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to connect to NBG API: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching NBG rates: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error fetching exchange rates: {str(e)}"
            )

    def _is_cache_valid(self, date_str: str) -> bool:
        """Check if cached data is still valid"""
        if date_str not in self._cache_timestamps:
            return False

        cache_age = (datetime.now() - self._cache_timestamps[date_str]).total_seconds()
        return cache_age < self.CACHE_TTL

    async def get_available_currencies(self, target_date: Optional[date] = None) -> list[str]:
        """
        Get list of available currencies.

        Args:
            target_date: Date for the exchange rates (default: today)

        Returns:
            List of currency codes
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime("%Y-%m-%d")

        # Check cache
        if self._is_cache_valid(date_str):
            cached_rates = self._cache.get(date_str, {})
            if cached_rates:
                return ["GEL"] + sorted(cached_rates.keys())

        # Fetch from API
        rates = await self._fetch_rates_from_api(target_date)
        return ["GEL"] + sorted(rates.keys())


# Singleton instance
_currency_service_instance: Optional[CurrencyService] = None


def get_currency_service() -> CurrencyService:
    """Get or create the currency service singleton"""
    global _currency_service_instance
    if _currency_service_instance is None:
        _currency_service_instance = CurrencyService()
    return _currency_service_instance
