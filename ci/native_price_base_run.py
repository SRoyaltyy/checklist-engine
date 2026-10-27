"""Run compact price operations with quota-aware, hash-verified artifact IO."""
from ci import native_price_base as base
from ci import native_price_blocks as sources
from ci.release_assets import gh_retry, download_asset


def main():
    original=(base.gh,base.download,sources.gh,sources.download)
    base.gh=sources.gh=gh_retry
    base.download=sources.download=download_asset
    try:base.main()
    finally:base.gh,base.download,sources.gh,sources.download=original


if __name__=="__main__":main()
