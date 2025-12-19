from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" ADD "given_name" VARCHAR(255);
        ALTER TABLE "users" ADD "family_name" VARCHAR(255);
        ALTER TABLE "users" ADD "family_name_required" BOOL NOT NULL DEFAULT False;
        UPDATE "users" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "users" DROP COLUMN "name";

        ALTER TABLE "pending_profiles" ADD "given_name" VARCHAR(255);
        ALTER TABLE "pending_profiles" ADD "family_name" VARCHAR(255);
        UPDATE "pending_profiles" SET "given_name" = COALESCE("given_name", "name");
        ALTER TABLE "pending_profiles" DROP COLUMN "name";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "pending_profiles" ADD "name" VARCHAR(511);
        UPDATE "pending_profiles" SET "name" = COALESCE("family_name", '') || ' ' || COALESCE("given_name", '');
        ALTER TABLE "pending_profiles" DROP COLUMN "family_name";
        ALTER TABLE "pending_profiles" DROP COLUMN "given_name";

        ALTER TABLE "users" ADD "name" VARCHAR(511);
        UPDATE "users" SET "name" = COALESCE("family_name", '') || ' ' || COALESCE("given_name", '');
        ALTER TABLE "users" DROP COLUMN "family_name_required";
        ALTER TABLE "users" DROP COLUMN "family_name";
        ALTER TABLE "users" DROP COLUMN "given_name";
    """


MODELS_STATE = (
    "eJztXetvmzoU/1ciPnVSV6VJ+tjV1ZXSLtty15fa9N5pvRNygkOtgsnAtI2m/O/XNhAwGB"
    "LSkMfiL7SxzzHwO36cl80vzXYMaHkH54+AaH/UfmkY2JD+I5Tv1zQwGsWlrICAvsUJB5SC"
    "l4C+R1wwYM0MgeVBWmRAb+CiEUEOZqT/+fXWYZ1dmy1+HfDrKb8a79mf1gn/wYlaDX7t13"
    "rQgqYLbHYXwxnQ2yBs0gaxb1m0yMfopw914piQPEKXVjw88MfSkcFYnuBY+/GD/oOwAV+h"
    "JxLQioeYZPSkDxG0DAGLoBlerpPxiJfd33c/fuKU7KH6+sCxfBvH1KMxeXTwlNz3kXHAeF"
    "idCTF0AYFGAir2LiGkUVHwXrSAuD6cPr4RFxhwCHyLAa79OfTxgOFc43dil9ZfWkYEIWIS"
    "EAcOZuJDmDB8fk2Ct4rfmZdq7FbnX9q3e83jd/wtHY+YLq/kiGgTzggICFg51jGQAxey19"
    "aDPiUC+pHWEGRDOagiZwpcI2Q9iP5ZBOSoIEY57sURzBF8i2Gq0XcwrrE1DiVYgHGve9m5"
    "67Uvb9ib2J730+IQtXsdVtPgpeNU6V4gEoeOwWBkThup/dvtfamxn7Xv11edtOCmdL3vGn"
    "sm4BNHx86LDoxEZ4tKI2AoZSxYf2QsKFiRUwl2rYINHz4xYONZVBTqGTK7mOSM1ZgpJU8K"
    "2HIkmJkA3yhAk93m/YdGo9k8adSbx6dHrZOTo9P6KaXlz5StOimQ8ln3c/eqJwqNFUwEcN"
    "mikwGWLriuHNaQPAUpfY3NhNQGr7oFsUke6c/DeqNVgNc/7Vu+qjCyVF+/CusaYeVkwpbp"
    "4VNifWEFfTB4egGuoWdqnIaTR5utsht2ugRgYHKA2Huydwg1o8+BFDMaEy8v1JhMSlFGYw"
    "r0oyZXhgLFqD+/JpTRezwCXKKzCVVpPErjUQuj0nh2WbAZjQeH0/e8q3JEX9WyvHTJCety"
    "4+hojmWZUuWuyrxO1GsSK0zJoSFyLmFohAJfndqzJQMhwqFwioPYWEiKST4lw9XLsISCnD"
    "BGkGXp8BniwJmXsvZC5k9fb6EFOJ5Z2Yb671faUIe1s5nz3yTqrVGpbBEYWWAM3TcCccMb"
    "2TIUqrSY4p4hMZuEbpNvO6W66XwWVOOQW1CQXw8DCyp2MAf+59awRv/UAa9ogoRjup+4Bk"
    "0wtnp/cSNMmV3K7FLauTK7dlewmRWXzevQZQvSELk2lHmcHceCAOf4RiXsKRH3KX9VUpWv"
    "PcuYA8+ury8ECZ51U37lq/vLs87t3iEXHSVCJM/dnMJogTGU08RKlPyKVKBNHztzWWrPiC"
    "7J9sKjR8auRs+kEOIFRk9OE2r0rHn0eAQQX2Ls5Tv9Yo6VReO0EcQGk8gbtAcxJHc8T0Au"
    "LZdEOO447fdj5pq7oHaW5lWDYs2DAnk6tcJd57n0apLiVAuJOEpY9FeaUpFv6CdYlmntr9"
    "OROtO2z+it5SATmHYQtHA+dcriluZ7A3QbNf+WgC5U08rhJjDtSH/LxBnESS4L3yfHhcjE"
    "X+GYg9ilzwHwQBYnSuXSbCpoGf85LXbBy9Szm5y56dvRd4LBsnDevjtvf+xokoluCbDde8"
    "uKO6wJNmH2FoC7pYrNbfe8p0mGrEIuNQ/Ngdx0vl8deGtbF2aCl178BPzuOr3a1f3FhTZZ"
    "T77hTWD/3bjOEHEcMyG0FMV+URwttCb1UUBcJh1xGCciBvGwVisTLTvdryXiZceJ+lZif0"
    "fA/SFRe1RL7AuBCYajxE0D5mSjpwuH4h4iW55vA/G9YNZRiZEqQlfpjPTbBHJUhO43FWwm"
    "QmeiZ4j1sumRItdC3tLV6wsryJEcAhtZ49JwptgUnhGeHIISQEb0W4lgszEHgM1GLn6sSo"
    "Rv4PiuB3Xs232ZBXpnA8vK3++VZl5o19caQA12fTUbJ8fTfV7sR9HOrrvL9sWFxKnrOv6o"
    "/OQocG1lV6xkMI8eHeJkgezB15weOGXYEgyLtILOt56gEERI7V22v70TlIKL66vPEXkC2f"
    "OL67MUoKDv+ET3PdnYzkdV5FLQyqG1LKpFPfqmycxpChDzXZWMmOW2oWJnmZ0lOxipX/5y"
    "jzwdw5fI+VM+vptiVt1UhJfagF6wM2DeqTbmUNOsdJodPAJsQiNyJWWg/fvu+ipHO81wpi"
    "C+x/TdHww0IPs1C3nkR1V9N+GZ6/vIIgh7B+yGFTnnGCTFckhDvi/6DFgDEjms/kCItZkG"
    "Kz4QwoaeB0x5dkgRviKfgrgAYs/v24gwLyPTa8sabHLuLZmyq1YqVMrJwiknUdypBGoJlm"
    "rTTTYHsYJ8E7lpu8bw/7pC2IluMTvhRAX/5w3+T+FbU+w/2Eosi/lPNxkXxPrj3cyLnjgU"
    "xuLDbbFBkL5RS0Tgk7RHmlww0nMao5HLM8aypzTyah6bjwlUYF4F5lX8VgXmd1OwmcA8xT"
    "n0NooyzTUXY4aqjmfMCu+4Xn+D7AJTsXHYOmmdNo9bUwtxWlJkGG7XFozNUbeVgaIMlDUb"
    "KBu3jWBdqM3cR7Aeu4R3R4lVEnXTfJuEdYPSScehFRKc3RPkCJ+kjuURjo4PsoajlOT5rZ"
    "LCHGFiqgxhZYgofVUZIjsuWJUhrDKEtwhPlSGsMoRVhvBvMphVhrDKEN4aaFWG8AzYl5h6"
    "GVjnWXALsqemLMvxhs+2v7cxb4qCtEjCVIptKTNE5QBXrEklNHTdhT995JY+YiuvCTUbZP"
    "LcEdblXuRZOe4JxspgzfTcbUEVGDaSJLjPPBcuYlOICojCV0QoUo5lOC9Y9zFBEgVhxkc3"
    "5E2o72+os0Vn71gCA4Ke4RsiAFWsmZloan6MSzxDi84znp53mNaufcokPlh11R932ZxUTw"
    "GQaQ/JOzRsd3tI8jCoxTHJHkO1nR1FdkTWClHZ1O6ivo1URSZFG7po8KhJcinCmv2ibAoQ"
    "08xKp8iHYcnfLcr1t8zrbAmnhQ3wtbwx8TA/xeGZDiQk2ymcrx4mWNQnJ2MfKx0aJUAMyb"
    "cTwMN6fQ4AKVXBl7Tr2fAeJqEaI4JYsLE6ZlnXjurK7Myl7Z0uYcQsf3mZ/A87eQoh"
)
