from ctenex.core.data_access.reader import GenericReader
from ctenex.domain.entities import Bid
from ctenex.domain.order_book.order_filter_params import BookOrderFilterParams


class BidFilter(BookOrderFilterParams):
    """Filter parameters for Bids."""


class BidReader(GenericReader[Bid]):
    """Reader for Bids."""

    model = Bid


bid_reader = BidReader()
