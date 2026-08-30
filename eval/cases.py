CASES = [
    {
        "name": "clean_auto_claim",
        "expected_decision": "auto_approve",
        "raw_text": """
        Claim ID: CLM-EVAL-001
        Policy Number: POL-11001
        Claimant: Meera Iyer
        Claim Type: auto
        Date of Incident: 2026-08-01
        Amount Claimed: $850.00
        Description: Side mirror cracked when a shopping cart rolled into the car in a parking lot.
        Contact: meera.iyer@example.com
        """,
    },
    {
        "name": "glass_damage_over_threshold",
        "expected_decision": "escalate",
        "raw_text": """
        Claim ID: CLM-EVAL-002
        Policy Number: POL-11002
        Claimant: Anita Rao
        Claim Type: auto
        Date of Incident: 2026-07-14
        Amount Claimed: $2,340.50
        Description: Rear windshield shattered by a fallen tree branch during a storm.
        Contact: anita.rao@example.com
        """,
    },
    {
        "name": "future_incident_date_invalid",
        "expected_decision": "auto_deny",
        "raw_text": """
        Claim ID: CLM-EVAL-003
        Policy Number: POL-11003
        Claimant: Rohan Verma
        Claim Type: auto
        Date of Incident: 2027-01-01
        Amount Claimed: $1,200.00
        Description: Front bumper damage from a minor collision.
        Contact: rohan.verma@example.com
        """,
    },
    {
        "name": "clean_home_storm_claim",
        "expected_decision": "auto_approve",
        "raw_text": """
        Claim ID: CLM-EVAL-004
        Policy Number: POL-11004
        Claimant: Sara Thomas
        Claim Type: home
        Date of Incident: 2026-08-10
        Amount Claimed: $3,200.00
        Description: Hailstorm damaged roof shingles on the south side of the house.
        Contact: sara.thomas@example.com
        """,
    },
    {
        "name": "excluded_racing_damage",
        "expected_decision": "escalate",
        "raw_text": """
        Claim ID: CLM-EVAL-005
        Policy Number: POL-11005
        Claimant: Vikram Nair
        Claim Type: auto
        Date of Incident: 2026-08-05
        Amount Claimed: $5,000.00
        Description: Vehicle damaged while competing in an amateur weekend racing event.
        Contact: vikram.nair@example.com
        """,
    },
    {
        "name": "home_claim_filed_late",
        "expected_decision": "escalate",
        "raw_text": """
        Claim ID: CLM-EVAL-006
        Policy Number: POL-11006
        Claimant: Divya Menon
        Claim Type: home
        Date of Incident: 2026-04-01
        Amount Claimed: $4,500.00
        Description: Water damage to living room ceiling discovered after a storm months ago; filing now.
        Contact: divya.menon@example.com
        """,
    },
]
