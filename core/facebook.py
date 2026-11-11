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


def safe(err) -> str:
    """Nội dung lỗi đã che mã (access_token) để hiện trên màn hình / ghi nhật ký không lộ mã."""
    import re
    return re.sub(r"(access_token=|OAuth\s+|Bearer\s+)[A-Za-z0-9_\-\.%]+", r"\1***", str(err))


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
            msg = "Mã Facebook thiếu quyền cho việc này (" + msg + "). Lấy mã lại và tick đủ quyền."
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


def set_thumbnail(video_id, token, image_path, ver="v23.0"):
    """Đặt ảnh bìa cho video/Reels đã tải lên."""
    with open(image_path, "rb") as f:
        r = requests.post(f"https://graph.facebook.com/{ver}/{video_id}/thumbnails",
                          data={"is_preferred": "true", "access_token": token},
                          files={"source": (os.path.basename(image_path), f, "image/jpeg")}, timeout=120)
    return _check(r)


def comment(object_id, token, message, ver="v23.0"):
    r = requests.post(f"https://graph.facebook.com/{ver}/{object_id}/comments",
                      data={"message": message, "access_token": token}, timeout=60)
    return _check(r)


def post(video_path: str, text: str, page: dict, scheduled_at: datetime, product_link: str = "",
         ver: str = "v23.0", cover: str = "") -> tuple:
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
    if cover and os.path.exists(cover):
        try:
            set_thumbnail(vid, page["token"], cover, ver)
            note += " + ảnh bìa riêng"
        except Exception as e:
            note += f" (đặt ảnh bìa lỗi, Facebook tự chọn bìa: {safe(e)[:120]})"
    if schedule_ts:
        return "scheduled_fb", note + f" — FB sẽ tự đăng lúc {scheduled_at:%d/%m %H:%M}"
    if product_link:
        try:
            comment(vid, page["token"], f"👉 Link sản phẩm em để đây nha bác: {product_link}", ver)
            note += " + đã bình luận link"
        except Exception as e:
            note += f" (bình luận link lỗi: {e})"
    return "done", note


# ======================= Kết nối trang, nhiệm vụ tuần, bình luận, Tin =======================
GRAPH = "https://graph.facebook.com"
PERMS = ["pages_show_list", "pages_read_engagement", "pages_manage_posts", "pages_read_user_content",
         "pages_manage_engagement", "business_management", "read_insights"]


def _get(path, token, ver="v23.0", **params):
    params["access_token"] = token
    return _check(requests.get(f"{GRAPH}/{ver}/{path.lstrip('/')}", params=params, timeout=60))


def pages_from_user_token(user_token: str, ver="v23.0") -> list:
    """Từ mã người dùng -> danh sách trang bác quản lý kèm mã trang.
    Mã người dùng dài hạn (60 ngày) cho ra mã trang KHÔNG hết hạn."""
    out, url = [], f"{GRAPH}/{ver}/me/accounts"
    params = {"fields": "id,name,access_token,followers_count", "limit": 100, "access_token": user_token}
    while url:
        data = _check(requests.get(url, params=params, timeout=60))
        out += data.get("data", [])
        url, params = data.get("paging", {}).get("next"), None
    return out


def token_expiry(token: str, ver="v23.0") -> str:
    """Hạn của mã (đọc được thì trả về chữ dễ hiểu, không thì chuỗi rỗng)."""
    try:
        d = _get("debug_token", token, ver, input_token=token).get("data", {})
        exp = int(d.get("expires_at") or 0)
        if not d.get("is_valid", True):
            return "Mã KHÔNG còn dùng được"
        return "Không hết hạn" if exp == 0 else f"Hết hạn ngày {datetime.fromtimestamp(exp):%d/%m/%Y}"
    except Exception:
        return ""


def page_info(page_id, token, ver="v23.0") -> dict:
    return _get(page_id, token, ver, fields="name,followers_count,fan_count,link")


def week_start(now: datetime = None) -> datetime:
    """Tuần nhiệm vụ của Facebook tính từ Chủ nhật 0:00 đến hết thứ Bảy."""
    from datetime import timedelta
    now = now or datetime.now()
    d = now - timedelta(days=(now.weekday() + 1) % 7)
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def _since(items, since: datetime, key):
    n = 0
    for it in items:
        try:
            t = datetime.strptime(it[key][:19], "%Y-%m-%dT%H:%M:%S")
            t = t.replace(tzinfo=__import__("datetime").timezone.utc).astimezone().replace(tzinfo=None)
            n += t >= since
        except Exception:
            pass
    return n


def week_counts(page_id, token, since: datetime, ver="v23.0") -> dict:
    """Đếm việc đã làm trong tuần: reels, bài viết (gồm cả reels), tin. Phần nào đọc lỗi thì để None."""
    ts = int(since.timestamp())
    out = {"reels": None, "posts": None, "stories": None}
    try:
        out["posts"] = _since(_get(f"{page_id}/published_posts", token, ver, since=ts, limit=100,
                                   fields="id,created_time").get("data", []), since, "created_time")
    except Exception:
        pass
    try:
        out["reels"] = _since(_get(f"{page_id}/video_reels", token, ver, limit=50,
                                   fields="id,created_time").get("data", []), since, "created_time")
    except Exception:
        pass
    try:
        st = _get(f"{page_id}/stories", token, ver, since=ts, limit=100).get("data", [])
        out["stories"] = sum(1 for s in st if str(s.get("status", "PUBLISHED")).upper() != "ARCHIVED"
                             and int(s.get("creation_time") or ts) >= ts)
    except Exception:
        pass
    return out


def unreplied_comments(page_id, token, days=7, ver="v23.0", limit=30) -> list:
    """Bình luận của người xem trong `days` ngày qua mà trang chưa trả lời."""
    from datetime import timedelta
    since = int((datetime.now() - timedelta(days=days)).timestamp())
    data = _get(f"{page_id}/published_posts", token, ver, since=since, limit=25,
                fields="id,message,permalink_url,comments.limit(50){id,message,created_time,from,"
                       "comments.limit(20){from}}").get("data", [])
    out = []
    for p in data:
        for c in (p.get("comments") or {}).get("data", []):
            if (c.get("from") or {}).get("id") == str(page_id):
                continue
            replies = (c.get("comments") or {}).get("data", [])
            if any((r.get("from") or {}).get("id") == str(page_id) for r in replies):
                continue
            out.append({"id": c["id"], "message": c.get("message", ""), "who": (c.get("from") or {}).get("name", "Người xem"),
                        "time": c.get("created_time", "")[:16].replace("T", " "),
                        "post": (p.get("message") or "")[:80], "link": p.get("permalink_url", "")})
    return out[:limit]


def reply_comment(comment_id, token, message, ver="v23.0"):
    return comment(comment_id, token, message, ver)


def post_story(page_id, token, path, ver="v23.0") -> str:
    """Đăng video vào Tin của trang (video 3-60 giây). Tin không hẹn giờ được nên đăng ngay."""
    base = f"{GRAPH}/{ver}/{page_id}/video_stories"
    start = _check(requests.post(base, params={"upload_phase": "start", "access_token": token}, timeout=60))
    vid = start["video_id"]
    url = start.get("upload_url") or f"https://rupload.facebook.com/video-upload/{ver}/{vid}"
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        _check(requests.post(url, data=f, timeout=1800, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)}))
    _check(requests.post(base, params={"upload_phase": "finish", "video_id": vid, "access_token": token},
                         timeout=120))
    return vid
