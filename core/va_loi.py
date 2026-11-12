"""Vá lỗi máy chủ giao diện: sau một lúc chạy, Streamlit (máy chủ starlette + anyio) có lúc báo
'NoEventLoopError: Not currently running on any asynchronous event loop' khi phục vụ trang -> cửa sổ app
hiện 'Internal Server Error' tới khi khởi động lại.
Nguyên nhân: trong luồng chạy máy chủ, dấu "vòng sự kiện đang chạy" của asyncio bị xoá mất (vòng sự kiện
thật vẫn chạy), nên anyio/sniffio tưởng không có vòng sự kiện nào.
Vá: khi anyio không nhận ra, nếu đang ở đúng luồng của vòng sự kiện Streamlit thì gắn lại dấu đó và trả lời
"asyncio". Import 1 lần là đủ (gọi lại không sao)."""
import asyncio
import threading


def _loop_streamlit():
    try:
        from streamlit.runtime import Runtime
        return Runtime.instance()._async_objs.eventloop
    except Exception:
        return None


def va_anyio():
    try:
        import anyio._core._eventloop as ev
    except Exception:
        return
    goc = ev.current_async_library
    if getattr(goc, "_sonix", False):
        return

    def current_async_library():
        r = goc()
        if r:
            return r
        try:
            asyncio.get_running_loop()
            return "asyncio"
        except RuntimeError:
            pass
        loop = _loop_streamlit()
        if loop is not None and loop.is_running() and getattr(loop, "_thread_id", None) == threading.get_ident():
            asyncio.events._set_running_loop(loop)  # gắn lại dấu bị xoá
            return "asyncio"
        return None

    current_async_library._sonix = True
    ev.current_async_library = current_async_library


va_anyio()
