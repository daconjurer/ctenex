from ctenex.core.data_access.reader import GenericReader
from ctenex.domain.entities import Ask
from ctenex.domain.order_book.order_filter_params import BookOrderFilterParams


class AskFilter(BookOrderFilterParams):
    """Filter parameters for Asks."""


class AskReader(GenericReader[Ask]):
    """Reader for Asks."""

    model = Ask


asks_reader = AskReader()
