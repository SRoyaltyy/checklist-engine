"""Active owner scope; historical release contents are never rewritten."""
NEWS_DROP_REASON='dropped by Cyrus 2026-10-28: tone is evaluated after the fact, so it is not usable live'
NEWS_DROP_AUTHORITY=('4e83be2','8a5bcdb','01587ff')
PUT_CALL_DROP_REASON=('dropped by Cyrus 2026-10-29 (James 9e545e9): '
                      'I201 CBOE put/call has no free daily 2020-2026 history and fails the live-replicable rule')
OWNER_DROPPED_ITEMS={'I200':NEWS_DROP_REASON,'I201':PUT_CALL_DROP_REASON}


def news_columns(columns):
    return [c for c in columns if str(c).lower().startswith(('gd_','gdelt_','news_'))]
