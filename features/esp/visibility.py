from functions import memfuncs


def resolve_local_index(processHandle, EntityList, local_controller_addr) -> int:
    try:
        for i in range(1, 65):
            list_entry = memfuncs.ProcMemHandler.ReadPointer(processHandle, EntityList + (8 * (i & 0x7FFF) >> 9) + 16)
            if not list_entry:
                continue
            controller = memfuncs.ProcMemHandler.ReadPointer(processHandle, list_entry + 112 * (i & 0x1FF))
            if controller == local_controller_addr:
                return i
    except Exception:
        return 0
    return 0


def is_visible_to_local(processHandle, pawn, Offsets, local_index: int) -> bool:
    try:
        if local_index > 0:
            base = pawn + Offsets.offset.m_entitySpottedState
            mask = memfuncs.ProcMemHandler.ReadInt(processHandle, base + Offsets.offset.m_bSpottedByMask)
            return bool(mask & (1 << (local_index - 1))) or bool(mask & (1 << local_index))
    except Exception:
        return False
    return False

