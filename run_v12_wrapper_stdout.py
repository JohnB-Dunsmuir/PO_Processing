from pathlib import Path
from diagnose_one_pdf import diagnose_one_pdf_wrapper

def run_v12_wrapper_stdout(pdf_path, parser_override=None, stdout=True):
    result = diagnose_one_pdf_wrapper(
        pdf_path=pdf_path,
        forced_parser=parser_override,  # 🔒 forced always wins
        stdout=stdout,
    )
    return {
        "source_file": Path(pdf_path).name,
        **result,
    }

if __name__ == "__main__":
    import sys
    run_v12_wrapper_stdout(sys.argv[1], stdout=True)