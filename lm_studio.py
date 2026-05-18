# -*- coding: utf-8 -*-
"""
LM Studio 本地 OpenAI 兼容接口
------------------------------
- 列表模型：``GET http://127.0.0.1:1234/v1/models``（每次 chat 前预检）
- 对话：``POST http://127.0.0.1:1234/v1/chat/completions``，模型 ``qwen/qwen3.5-9b``，
  ``temperature=0.2``；从 ``choices[0].message`` 取正文时**优先** ``content``，
  为空再读 ``reasoning_content`` / ``reasoning``（Qwen 思考链常把 JSON 放在后者）。
- Chat 默认 ``timeout=180``（含 reasoning 时往往 >30s，过短会误报网络失败）。
- HTTP 非 2xx 时 ``raise_for_status()`` 并打印详细错误。

依赖：``pip install requests``（见项目 ``requirements.txt``）。
"""

import json
import re
import traceback
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError as _e:  # pragma: no cover
    raise ImportError(
        "请先安装 requests：pip install requests\n原始错误：%s" % _e
    ) from _e

LM_STUDIO_BASE = "http://127.0.0.1:1234"
LM_MODELS_URL = LM_STUDIO_BASE + "/v1/models"
LM_CHAT_URL = LM_STUDIO_BASE + "/v1/chat/completions"
MODEL_NAME = "qwen/qwen3.5-9b"
LM_STUDIO_URL = LM_CHAT_URL

# 预检可较短；对话含 reasoning 时常需 1～3 分钟
MODELS_TIMEOUT = 30
REQUEST_TIMEOUT = 180


class LMStudioNetworkError(Exception):
    """无法连接 LM Studio 或请求失败。"""


class LMStudioJsonError(Exception):
    """模型返回内容不是合法 JSON（或缺字段）。"""

    def __init__(self, message, phase="parse"):
        # type: (str, str) -> None
        super(LMStudioJsonError, self).__init__(message)
        self.phase = phase


def _log_error(where, err):
    # type: (str, Exception) -> None
    print("========== [lm_studio] %s ==========" % where)
    print("模型:", MODEL_NAME)
    print("异常类型:", type(err).__name__)
    print("异常信息:", repr(err))
    traceback.print_exc()
    print("========================================")


def _log_http_error(where, response, err=None):
    # type: (str, Any, Any) -> None
    print("========== [lm_studio] %s ==========" % where)
    print("模型:", MODEL_NAME)
    print("URL:", getattr(response, "url", ""))
    print("HTTP 状态:", getattr(response, "status_code", "?"))
    print("响应正文:", ((getattr(response, "text", None) or "")[:1200]))
    if err is not None:
        print("异常类型:", type(err).__name__)
        print("异常信息:", repr(err))
        traceback.print_exc()
    print("========================================")


def _text_field(value):
    # type: (Any) -> str
    """安全取字符串；``None`` 与 JSON ``null`` 均视为空。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def ensure_lm_studio_ready(timeout=MODELS_TIMEOUT):
    # type: (int) -> None
    try:
        r = requests.get(LM_MODELS_URL, timeout=timeout)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            _log_http_error("GET /v1/models HTTP 错误", r, e)
            raise LMStudioNetworkError(
                "GET /v1/models 失败 HTTP %s：%s"
                % (r.status_code, (r.text or "")[:800])
            ) from e
    except LMStudioNetworkError:
        raise
    except requests.exceptions.RequestException as e:
        _log_error("GET /v1/models 请求异常", e)
        raise LMStudioNetworkError(
            "无法连接 LM Studio（%s）：%s" % (LM_MODELS_URL, e)
        ) from e


def _assistant_message_text(message, choice=None, merge_all=False):
    # type: (Any, Any, bool) -> str
    """
    默认：优先 ``content``，为空再读 ``reasoning_content`` / ``reasoning``。

    ``merge_all=True`` 时拼接 content + reasoning（去重），供 JSON 抽取：
    Qwen 思考链常在 reasoning 里写完整 JSON，而 content 只有短句或空。
    """
    parts = []  # type: List[str]
    seen = set()  # type: set

    def _add_block(text):
        # type: (str) -> None
        if text and text not in seen:
            seen.add(text)
            parts.append(text)

    if isinstance(message, dict):
        if merge_all:
            for key in ("content", "reasoning_content", "reasoning"):
                _add_block(_text_field(message.get(key)))
        else:
            content = _text_field(message.get("content"))
            if content:
                return content
            for key in ("reasoning_content", "reasoning"):
                t = _text_field(message.get(key))
                if t:
                    return t
    if isinstance(choice, dict):
        _add_block(_text_field(choice.get("text")))
    if merge_all:
        return "\n\n".join(parts)
    if parts:
        return parts[0]
    return ""


def chat_completion(
    messages,
    temperature=0.2,
    timeout_sec=REQUEST_TIMEOUT,
):
    # type: (List[Dict[str, str]], float, int) -> str
    ensure_lm_studio_ready(timeout=MODELS_TIMEOUT)

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    try:
        res = requests.post(
            LM_CHAT_URL,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=timeout_sec,
        )
        try:
            res.raise_for_status()
        except requests.HTTPError as e:
            _log_http_error("POST /v1/chat/completions HTTP 错误", res, e)
            raise LMStudioNetworkError(
                "POST chat/completions 失败 HTTP %s：%s"
                % (res.status_code, (res.text or "")[:1200])
            ) from e
    except LMStudioNetworkError:
        raise
    except requests.exceptions.Timeout as e:
        _log_error("POST /v1/chat/completions 超时", e)
        raise LMStudioNetworkError(
            "请求超时（%s 秒）：本地模型含思考链时较慢，请稍候重试或增大 timeout。"
            % timeout_sec
        ) from e
    except requests.exceptions.RequestException as e:
        _log_error("POST /v1/chat/completions 请求异常", e)
        raise LMStudioNetworkError(
            "无法连接或超时（%s）：%s" % (LM_CHAT_URL, e)
        ) from e

    try:
        data = res.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            raise KeyError("choices")
        ch0 = choices[0]
        if not isinstance(ch0, dict):
            raise TypeError("choices[0] 不是对象")
        msg = ch0.get("message")
        if not isinstance(msg, dict):
            raise KeyError("message")
        return _assistant_message_text(msg, ch0, merge_all=True)
    except (KeyError, IndexError, TypeError, ValueError) as e:
        _log_error("解析 chat 响应 JSON", e)
        raise LMStudioNetworkError(
            "响应 JSON 结构异常：%s | 正文前500字：%s" % (e, (res.text or "")[:500])
        ) from e


def _extract_first_balanced_json_object(text):
    # type: (str) -> Optional[str]
    s = (text or "").strip()
    i = s.find("{")
    if i < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for j in range(i, len(s)):
        ch = s[j]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[i : j + 1]
    return None


_THINK_STRIP_PATTERNS = (
    re.compile(r"``[\s\S]*?``", re.DOTALL | re.IGNORECASE),
    re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE | re.DOTALL),
)


def _strip_thinking_markers(text):
    # type: (str) -> str
    t = text or ""
    for _ in range(8):
        prev = t
        for pat in _THINK_STRIP_PATTERNS:
            t = pat.sub("", t)
        t = t.strip()
        if t == prev:
            break
    return t


def _collect_balanced_json_substrings(text):
    # type: (str) -> List[str]
    s = text or ""
    out = []  # type: List[str]
    seen = set()  # type: set
    for j in range(len(s) - 1, -1, -1):
        if s[j] != "{":
            continue
        sub = _extract_first_balanced_json_object(s[j:])
        if sub and sub not in seen:
            seen.add(sub)
            out.append(sub)
    return out


def _score_dict_keys(obj, required_keys):
    # type: (Dict[str, Any], tuple) -> int
    return sum(1 for k in required_keys if k in obj)


def _coerce_json_values(obj):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """将值统一为字符串（模型偶发返回数字/列表）。"""
    out = {}  # type: Dict[str, Any]
    for k, v in obj.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, str):
            out[k] = v.strip()
        elif isinstance(v, (list, tuple)):
            out[k] = "\n".join(str(x).strip() for x in v if x is not None)
        elif isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v).strip()
    return out


def extract_json_object(text, phase="parse", required_keys=None):
    # type: (str, str, Any) -> Dict[str, Any]
    req = tuple(required_keys) if required_keys else ()  # type: tuple

    t = (text or "").strip()
    if t.startswith("\ufeff"):
        t = t.lstrip("\ufeff").strip()

    t = _strip_thinking_markers(t)

    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t, re.IGNORECASE)
    if m:
        t = m.group(1).strip()

    candidates = [t]
    balanced = _extract_first_balanced_json_object(t)
    if balanced and balanced not in candidates:
        candidates.append(balanced)
    s0, e0 = t.find("{"), t.rfind("}")
    if s0 >= 0 and e0 > s0:
        slice_greedy = t[s0 : e0 + 1]
        if slice_greedy not in candidates:
            candidates.append(slice_greedy)
    for sub in _collect_balanced_json_substrings(t):
        if sub not in candidates:
            candidates.append(sub)

    last_err = None  # type: Optional[Exception]
    best = None  # type: Optional[Dict[str, Any]]
    best_score = -1

    for cand in candidates:
        if not cand:
            continue
        try:
            obj = json.loads(cand)
            if not isinstance(obj, dict):
                continue
            obj = _coerce_json_values(obj)
            if not req:
                return obj
            score = _score_dict_keys(obj, req)
            if score == len(req):
                return obj
            if score > best_score:
                best_score = score
                best = obj
        except json.JSONDecodeError as err:
            last_err = err
            continue

    if best is not None and best_score > 0:
        return best

    raise LMStudioJsonError(
        "返回不是合法 JSON" if last_err is None else "返回不是合法 JSON：%s" % last_err,
        phase=phase,
    )


def extract_json_object_setting(text):
    # type: (str) -> Dict[str, Any]
    keys = (
        "人设详情",
        "世界观详情",
        "修炼体系",
        "金手指详情",
        "剧情框架",
        "最终提示词",
    )
    return extract_json_object(text, phase="setting", required_keys=keys)
