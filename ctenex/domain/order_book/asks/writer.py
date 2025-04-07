from ctenex.core.data_access.writer import GenericWriter
from ctenex.domain.entities import Ask


class AskWriter(GenericWriter[Ask]):
    model = Ask


ask_writer = AskWriter()
