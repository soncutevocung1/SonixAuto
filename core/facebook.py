"""Đăng video lên Trang Facebook bằng API chính thức của Meta (Graph API).

- Video dọc 9:16, dài 3-90 giây  -> đăng dạng Reels.
- Video khác                    -> đăng dạng video thường.
- Hẹn giờ do chính Facebook giữ  -> đẩy lên trước, tới giờ FB tự đăng (máy tắt cũng được).
"""
import os
from datetime import datetime

import requests

from .video_utils import probe


class FacebookError(Exception):
    pass


def _check(r: requests.Response) -> dict:
    try:
        data = r.json()
    except Exception:
        raise FacebookError(f"FB trả về lỗi HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        msg = err.get("error_user_msg") or err.get("message") or str(data)[:300]
        code = err.get("code")
        if code == 190:
            msg = "Token Facebook hết hạn hoặc sai. Vào Cài đặt lấy token mới. (" + msg + ")"
        elif code in (10, 200):
            msg = "Token thiếu quyền đăng bài (cần pages_manage_posts, publish_video). (" + msg + ")"
        raise FacebookError(msg)
    return data


def check_token(page_id: str, token: str, ver: str = "v23.0") -> str:
    r = requests.get(f"https://graph.facebook.com/{ver}/{page_id}",
                     params={"fields": "name", "access_token": token}, timeout=30)
    return _check(r).get("name", "?")


def _upload_reel(page_id, token, path, description, schedule_ts, ver):
    base = f"https://graph.facebook.com/{ver}/{page_id}/video_reels"
    start = _check(requests.post(base, params={"upload_phase": "start", "access_token": token}, timeout=60))
    video_id = start["video_id"]
    upload_url = start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{ver}/{video_id}"
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        r = requests.post(upload_url, data=f, timeout=1800, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    _check(r)
    params = {"upload_phase": "finish", "video_id": video_id, "description": description,
              "access_token": token}
    if schedule_ts:
        params.update(video_state="SCHEDULED", scheduled_publish_time=str(schedule_ts))
    else:
        params["video_state"] = "PUBLISHED"
    _check(requests.post(base, params=params, timeout=120))
    return video_id


def _upload_video(page_id, token, path, description, schedule_ts, ver):
    url = f"https://graph-video.facebook.com/{ver}/{page_id}/videos"
    data = {"description": description, "access_token": token}
    if schedule_ts:
        data.update(published="false", scheduled_publish_time=str(schedule_ts))
    with open(path, "rb") as f:
        r = requests.post(url, data=data, files={"source": (os.path.basename(path), f, "video/mp4")},
                          timeout=3600)
    return _check(r).get("id")


def comment(object_id, token, message, ver="v23.0"):
    r = requests.post(f"https://graph.facebook.com/{ver}/{object_id}/comments",
                      data={"message": message, "access_token": token}, timeout=60)
    return _check(r)


def post(video_path: str, text: str, page: dict, scheduled_at: datetime, product_link: str = "",
         ver: str = "v23.0") -> tuple:
    """Đăng/hẹn giờ. Trả về (status, ghi_chú). status: 'done' hoặc 'scheduled_fb'."""
    if not page.get("page_id") or not page.get("token"):
        raise FacebookError(f"Trang '{page.get('name')}' chưa có Page ID hoặc token (vào Cài đặt).")
    delta = (scheduled_at - datetime.now()).total_seconds()
    schedule_ts = int(scheduled_at.timestamp()) if delta >= 15 * 60 else None

    info = probe(video_path)
    is_reel = (info["height"] > info["width"] > 0) and 3 <= info["duration"] <= 90
    kind = "Reels" if is_reel else "Video"
    try:
        if is_reel:
            vid = _upload_reel(page["page_id"], page["token"], video_path, text, schedule_ts, ver)
        else:
            vid = _upload_video(page["page_id"], page["token"], video_path, text, schedule_ts, ver)
    except FacebookError:
        if not is_reel:
            raise
        kind = "Video (Reels lỗi, đăng dạng thường)"
        vid = _upload_video(page["page_id"], page["token"], video_path, text, schedule_ts, ver)

    note = f"{kind} id={vid}"
    if schedule_ts:
        return "scheduled_fb", note + f" — FB sẽ tự đăng lúc {scheduled_at:%d/%m %H:%M}"
    if product_link:
        try:
            comment(vid, page["token"], f"👉 Link sản phẩm em để đây nha bác: {product_link}", ver)
            note += " + đã bình luận link"
        except Exception as e:
            note += f" (bình luận link lỗi: {e})"
    return "done", note
