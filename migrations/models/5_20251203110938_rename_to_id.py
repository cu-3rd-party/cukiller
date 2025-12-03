from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "kill_events" RENAME COLUMN "victim_user_id" TO "victim_id";
        ALTER TABLE "kill_events" RENAME COLUMN "killer_user_id" TO "killer_id";
            """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "kill_events" RENAME COLUMN "victim_id" TO "victim_user_id";
        ALTER TABLE "kill_events" RENAME COLUMN "killer_id" TO "killer_user_id";
            """


MODELS_STATE = (
    "eJztXetvmzoU/1ciPnVSVyXk1V1dXSntsi13falN753WOyEHnBSVRwamD035369tIGAMlN"
    "AQksVfaGOfA+F3bJ+nnV+SaWvQcI9O7wGS/mj8kixgQvwP037YkMB8HrWSBgQmBiVUMQVt"
    "ARMXOUAlt5kCw4W4SYOu6uhzpNsWIf3Pa3ZaTXJtd+hVpddjetXekz+dPv1AiToyvU4aY2"
    "jAmQNM8hTNVvFjdGuGb2h5hoGbPEv/6UEF2TOI7qGDO+7u6NdSdI2wPMAX6ccP/I9uafAZ"
    "uiwB7riLSOYPylSHhsZg4d+GtivoZU7bbm9HHz9RSvKlJopqG55pRdTzF3RvW0tyz9O1I8"
    "JD+mbQgg5AUItBRd4lgDRs8t8LNyDHg8uvr0UNGpwCzyCAS39OPUslODfok8il85fEiSBA"
    "LAVE1baI+HQLEXx+Lfy3it6ZtkrkUadfBtcH7d47+pa2i2YO7aSISAvKCBDwWSnWEZCqA8"
    "lrK/6YYgH9iHuQbsJ0UFnOBLhawHoU/lMG5LAhQjkaxSHMIXzlMJXwO2iXlvESSDAH4/Ho"
    "fHgzHpxfkTcxXfenQSEajIekR6atL4nWA18kNp6D/sxc3qTx72j8pUE+Nr5fXgyTglvSjb"
    "9L5DsBD9mKZT8pQIsNtrA1BAZTRoL15lpJwbKcQrC1Cjb48rEJG62irFBP9NnIQhlzNWJK"
    "yBMDth4JcgvgGwU4I495/0GW2+2+3Gz3jrudfr973DzGtPQ78V39HCmfjD6PLsas0EjDgg"
    "GXKB0OWKxwnXRYA/IEpPg1thNSEzwrBrRm6B5/bDXlTg5e/wyuqVYhZImxfhH0yUHnYkHU"
    "9PQhpl9IwwSoD0/A0RSux5btLFq+y5TNZAuwwIwCRN6TvENgGX32pchZTLQ912KaYYpVLC"
    "bfPmpTY8g3jCbFLSHO7nERcJBCFlRh8QiLRyhGYfHss2A5i8cKlu+iWjmkr0otr11yjF6W"
    "u90CahlTZWpl2sfaNTENs+LUYDnXMDUCgW/O7NmRiRDikLvEQUsrJcU4n5Dh5mW4goEcc0"
    "Z0w1DgI7T8YF7C2wuYP329hgagePKyDezfr/hGQ3Kf7Vz/FuFoDVvTlMDcAC/QeSMQV/Qm"
    "O4ZClR5TNDJS3CZm2GT7TolhWsyDklvUg4L02vI9qCjA7MefO9MG/tMEtKMNYoHpSezq34"
    "KwNSflnTDhdgm3S1jnwu3aX8FyGpes69AhCmmqOyZMizjbtgGBlREbTWFPiHiC+auSarru"
    "WccaeHJ5ecZI8GSUiCtf3J6fDK8PWlR0mEhHWeHmBEYl5lDGLTZi5FdkAm373CnkqT3qWC"
    "WbpWdPGruYPYtciEvMnoxbiNlT8+xxEUBeirOXHfSLODaWjZPm0NKIRN5gPbApuV6RhFxS"
    "LrF0XC8Z9yPumlPSOkvyiklR86TQXQV74Y79uLI2SXAKRcLOEpL9TS2pyHb0Yyzr9PbrDK"
    "S+6ttzdqvn4stquPGcewhfsLLaq4KX5HsDdFu1Eq8AXWCwlRh5POeejDwu98AufDyGn2wH"
    "6jPrK3yhSI7w9wCWmpY7StTXbCtoXEwdNzvgaRntja/m+O3wO0FfVZwObk4HH4dS1uK3Bu"
    "xu3XUlJGrCjl/RGQivsdlzPTodS1nTWGCYtjYVwHCpDTaHYG1a41UEk6qRwe9mOG5c3J6d"
    "SYt66hKvfD/xyrGnOsWRS7UlKA7z8m2B16nMfeJVyhanUcGinzfrdLis2vFhI5ZX68X6O7"
    "F9ID73h1hvtxHbPwJjDN3YQ33m+E2PS6fs7kKfn24XCeeOKKAUmbxKV6TfJuEjMnm/qWDr"
    "LaDcvI3ABlG7rVaBKCqmygyj0j7W7aQQrIBgSL+TCLblAgC25Uz8SBcLn2p7jgsVyzMnaQ"
    "b/jQkMI3vvUpK51A6mGkD1dzC15X5vuWeJfMjbpXRzPjg7SwlQOrY3V1adxizXTg7FSoqh"
    "5/c2snkgx/A5YwQuGXYEwzzNNfw2ZpRWiNTB+eDbO0ZxnV1efA7JY8ienl2eJAAFE9tDGc"
    "58Nqosl4A2Fdr9TISuXwPprmLBp9BnXj19lmAWGTQWXmw6u37hddHZH3GImZ8689V7YM2w"
    "SxV44By0f99cXmQYTBxnAuJbC7/7naar6LBh6C76UdXYjQU0Jp5uIN1yj8gDK4ppEEjy5Z"
    "CE/JB1tcgNUuSw+f32tVmrG95vb0LXBbP05HseviyfgDgHYtebmDoiwRliaq3qQ6Rz78iS"
    "XbVRIfL4pfP4JRL4G8vcbw9iOan7rUud1pX5y0qapubuRc60aM50CV9NKVN/p2ZaqnS5hz"
    "MnRRptFi17oEuQwgx2Hfq5TbkRS1zGabvFk5h3y5lLi2/4Q/BoN01pRgQinynymSLtJfKZ"
    "+ylYLp+JcQ6ijaxMM93FiKGq0+944fWazTfIzncV5Van3zlu9zpLD3HZkucY7laF+/aY28"
    "JBEQ5KzQ7K1lVk14XaqyXZ9fgldDimeCXhMM32ScgwWLlWM/BC/KNR/NLKfuLUE+Zkbr/Y"
    "MqzkLO6V5JZWopkorBSOiLBXhSOy54IVhZXZkhOFlaKwUhRW7sxQFIWVu1ADJAorK4PWd2"
    "o4VPOKTpYs6wkivu627GK5CQapTJ1Jgm0tg7ZygKuvWdUtJT0i9Fq9aoyxslpVDs6dKFUl"
    "Z+Fopp5SrPrqETohm0B0B2vUgYr0R/iGmE8V052Ln2dHNdkDKPBodBX/6IWUgbxnZ4NHJ5"
    "Vt+rT07Snu4Y4ooSPEP1hCjJBohMRPTSiPCX9ew24OlLSzJDaIyrYOF/FjA1XkzgbQ0dV7"
    "KSV7FvQc5uXPQETzWgItG4Y1/xBApqtY1E8MloUtcBPfWGqSndR6xBNJT9sblm0exljEbz"
    "hFwSA8NVYAMSDfTQBbzWYBADFVzk9TNvlguYUCM6bwVrqIpa49dJWF1da2W24FJ2b96mXx"
    "P1AZPa0="
)
