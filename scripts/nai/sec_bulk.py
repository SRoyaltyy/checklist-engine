"""Compatibility entry point for the versioned SEC retained-cohort collector."""
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    from ci.sec_bulk_retained import main
    main()
