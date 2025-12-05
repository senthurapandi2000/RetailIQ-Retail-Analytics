from src.data_cleaner import DataCleaner
from src.data_loader import DataLoader
from src.data_validator import DataValidator


def main() -> None:
    loader = DataLoader()
    retail_df = loader.load_data()

    validator = DataValidator(retail_df)
    validator.save_reports()

    # Release the validator and its DataFrame copy before cleaning.
    del validator

    cleaner = DataCleaner(retail_df)
    cleaned_df, cleaning_summary = cleaner.clean_data()

    print("\n" + "=" * 65)
    print("CLEANING SUMMARY")
    print("=" * 65)
    print(cleaning_summary.to_string(index=False))

    cleaner.save_outputs(
        cleaned_df=cleaned_df,
        summary=cleaning_summary,
    )


if __name__ == "__main__":
    main()