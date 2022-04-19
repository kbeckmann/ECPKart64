from construct import *
from ..mailbox import *

__all__ = ["Commander"]

CommandTypeT = Enum(Int32ub,
    COMMAND_INVALID = 0,
    COMMAND_PEEK    = 1,
    COMMAND_POKE    = 2,
    COMMAND_EXECUTE = 3,
)

CommandPeekT = Struct(
    "type"                / Const(int(CommandTypeT.COMMAND_PEEK), Int32ub),
    "address"             / Hex(Int32ub),
    "length"              / Hex(Int32ub),
)

CommandPokeT = Struct(
    "type"                / Const(int(CommandTypeT.COMMAND_POKE), Int32ub),
    "address"             / Hex(Int32ub),
    "data"                / GreedyBytes,
)

CommandExecuteT = Struct(
    "type"                / Const(int(CommandTypeT.COMMAND_EXECUTE), Int32ub),
    "address"             / Hex(Int32ub),
)

def dbg(*args):
    if False:
    # if True:
        print(*args)

class Commander():
    def __init__(self, mailbox: Mailbox) -> None:
        self.mailbox = mailbox

    def peek(self, address, length):
        dbg(f"Peek @{address:08x} {length}")
        chunk_words = 59
        chunk_bytes = chunk_words * 4
        full_chunks = length // chunk_bytes
        remainder = length % chunk_bytes

        data = b""
        for chunk in range(full_chunks):
            self.mailbox.tx(CommandPeekT.build(dict(
                address=address + chunk * chunk_bytes,
                length=chunk_words)))
            data += self.mailbox.rx()
        
        if remainder > 0:
            self.mailbox.tx(CommandPeekT.build(dict(
                address=address + full_chunks * chunk_bytes,
                length=remainder // 4)))
            data += self.mailbox.rx()

        return data

    def poke(self, address, data):
        dbg(f"Poke @{address:08x}={data}")

        chunk_words = 59
        chunk_bytes = chunk_words * 4
        chunks = (len(data) + chunk_bytes - 1) // chunk_bytes

        for chunk in range(chunks):
            self.mailbox.tx(CommandPokeT.build(dict(
                address=address + chunk * chunk_bytes,
                data=data[chunk * chunk_bytes:(chunk + 1) * chunk_bytes])))

    def execute(self, address):
        self.mailbox.tx(CommandExecuteT.build(dict(address=address)))
