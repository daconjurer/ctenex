from ctenex.core.data_access.writer import GenericWriter
from ctenex.domain.entities import Bid


class BidWriter(GenericWriter[Bid]):
    model = Bid


bid_writer = BidWriter()
