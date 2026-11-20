"""Chot chan goi key API tinh phi: chi cho phep khi SONIX_CHO_PHEP_API=1 (anh Son da dong y cho lan chay nay).
Xem CLAUDE.md o goc repo."""
import os, sys


def cho_phep(viec):
    if os.environ.get("SONIX_CHO_PHEP_API") == "1":
        return True
    sys.exit(f"DUNG: '{viec}' can goi key API tinh phi. Hoi anh Son truoc; neu dong y thi chay lai voi SONIX_CHO_PHEP_API=1.")
