from src.database import DatabaseBuilder


def main() -> None:
    builder = DatabaseBuilder()
    builder.build_database()


if __name__ == "__main__":
    main()