#!/usr/bin/env python3
"""
Canadian Public Service & Healthcare Retirement Cash Flow Calculator (2026 Ontario Tax Engine)
Run in PowerShell: python retirement_calculator.py
Zero external dependencies required (uses Python standard library only).
"""

import csv
import os
from dataclasses import dataclass
from typing import List


@dataclass
class ScenarioInput:
    name: str
    category: str  # "Randy" or "Paula" or "Custom"
    employment_income: float = 0.0
    pension_income: float = 0.0
    cpp_income: float = 0.0
    oas_income: float = 0.0
    rrsp_withdrawal: float = 0.0
    age: int = 64
    is_working: bool = True
    pssa_rate: float = 0.06002
    union_rate: float = 0.01627
    health_dental_benefits: float = 0.0
    work_expenses: float = 0.0
    sdb_annual: float = 0.0


@dataclass
class TaxAndNetResult:
    name: str
    gross_income: float
    pssa_deduction: float
    union_dues: float
    cpp_deduction: float
    ei_deduction: float
    fed_tax_gross: float
    prov_tax_gross: float
    ontario_surtax: float
    health_premium: float
    total_credits_savings: float
    fed_tax_net: float
    prov_tax_net: float
    total_tax: float
    other_deductions: float
    annual_net_cash: float
    biweekly_net_cash: float
    monthly_net_cash: float
    effective_tax_rate: float


def calculate_2026_ontario_tax_and_net(s: ScenarioInput) -> TaxAndNetResult:
    gross = (
        s.employment_income
        + s.pension_income
        + s.cpp_income
        + s.oas_income
        + s.rrsp_withdrawal
    )

    # 1. Statutory & Payroll Deductions (Only on Employment Income)
    if s.is_working and s.employment_income > 0:
        pssa = s.employment_income * s.pssa_rate
        union = s.employment_income * s.union_rate

        # 2026 EI: 1.63% up to Max Insurable Earnings $68,900 -> max $1,123.07
        ei_insurable = min(s.employment_income, 68900.0)
        ei = ei_insurable * 0.0163

        # 2026 CPP: 5.95% on ($3,500 to $74,600) + CPP2 4.0% on ($74,600 to $85,000)
        cpp1_earnings = max(0.0, min(s.employment_income, 74600.0) - 3500.0)
        cpp1 = cpp1_earnings * 0.0595
        cpp2_earnings = max(0.0, min(s.employment_income, 85000.0) - 74600.0)
        cpp2 = cpp2_earnings * 0.04
        cpp = cpp1 + cpp2
    else:
        pssa = 0.0
        union = 0.0
        ei = 0.0
        cpp = 0.0

    # Taxable Income (PSSA & Union Dues are tax-deductible from gross income)
    taxable_income = max(0.0, gross - pssa - union)

    # 2. 2026 Federal Gross Tax
    if taxable_income <= 58523.0:
        fed_gross = taxable_income * 0.14
    elif taxable_income <= 117045.0:
        fed_gross = (58523.0 * 0.14) + ((taxable_income - 58523.0) * 0.205)
    else:
        fed_gross = (
            (58523.0 * 0.14)
            + ((117045.0 - 58523.0) * 0.205)
            + ((taxable_income - 117045.0) * 0.26)
        )

    # 3. 2026 Ontario Provincial Gross Tax
    if taxable_income <= 53891.0:
        prov_gross = taxable_income * 0.0505
    elif taxable_income <= 107785.0:
        prov_gross = (53891.0 * 0.0505) + ((taxable_income - 53891.0) * 0.0915)
    else:
        prov_gross = (
            (53891.0 * 0.0505)
            + ((107785.0 - 53891.0) * 0.0915)
            + ((taxable_income - 107785.0) * 0.1116)
        )

    # 4. Non-Refundable Tax Credits (2026 Indexed)
    fed_bpa_credit = 16452.0 * 0.14
    prov_bpa_credit = 12989.0 * 0.0505
    fed_emp_credit = (
        (min(s.employment_income, 1471.0) * 0.14)
        if s.employment_income > 0
        else 0.0
    )
    fed_cpp_ei_credit = (cpp + ei) * 0.14
    prov_cpp_ei_credit = (cpp + ei) * 0.0505

    eligible_pension = s.pension_income
    fed_pension_credit = min(eligible_pension, 2000.0) * 0.14
    prov_pension_credit = min(eligible_pension, 1714.0) * 0.0505

    if s.age >= 65:
        fed_age_base = 9208.0
        fed_age_clawback = max(0.0, (taxable_income - 45522.0) * 0.15)
        fed_age_credit = max(0.0, fed_age_base - fed_age_clawback) * 0.14

        prov_age_base = 6351.0
        prov_age_clawback = max(0.0, (taxable_income - 46330.0) * 0.15)
        prov_age_credit = max(0.0, prov_age_base - prov_age_clawback) * 0.0505
    else:
        fed_age_credit = 0.0
        prov_age_credit = 0.0

    total_fed_credits = (
        fed_bpa_credit
        + fed_emp_credit
        + fed_cpp_ei_credit
        + fed_pension_credit
        + fed_age_credit
    )
    total_prov_credits = (
        prov_bpa_credit
        + prov_cpp_ei_credit
        + prov_pension_credit
        + prov_age_credit
    )

    fed_net = max(0.0, fed_gross - total_fed_credits)
    prov_basic_net = max(0.0, prov_gross - total_prov_credits)

    # 5. Ontario Surtax
    surtax = 0.0
    if prov_basic_net > 5818.0:
        surtax += (prov_basic_net - 5818.0) * 0.20
    if prov_basic_net > 7446.0:
        surtax += (prov_basic_net - 7446.0) * 0.36

    # 6. Ontario Health Premium (OHP)
    if taxable_income <= 20000.0:
        ohp = 0.0
    elif taxable_income <= 25000.0:
        ohp = min(300.0, (taxable_income - 20000.0) * 0.06)
    elif taxable_income <= 38500.0:
        ohp = 300.0
    elif taxable_income <= 48000.0:
        ohp = 375.0
    elif taxable_income <= 72000.0:
        ohp = 600.0
    elif taxable_income <= 200000.0:
        ohp = 750.0
    else:
        ohp = 900.0

    prov_net = prov_basic_net + surtax + ohp
    total_tax = fed_net + prov_net
    other_deductions = (
        s.health_dental_benefits + s.work_expenses + s.sdb_annual
    )

    annual_net = gross - (
        pssa + union + cpp + ei + total_tax + other_deductions
    )
    eff_rate = (total_tax / gross * 100.0) if gross > 0 else 0.0

    return TaxAndNetResult(
        name=s.name,
        gross_income=gross,
        pssa_deduction=pssa,
        union_dues=union,
        cpp_deduction=cpp,
        ei_deduction=ei,
        fed_tax_gross=fed_gross,
        prov_tax_gross=prov_gross,
        ontario_surtax=surtax,
        health_premium=ohp,
        total_credits_savings=total_fed_credits + total_prov_credits,
        fed_tax_net=fed_net,
        prov_tax_net=prov_net,
        total_tax=total_tax,
        other_deductions=other_deductions,
        annual_net_cash=annual_net,
        biweekly_net_cash=annual_net / 26.0,
        monthly_net_cash=annual_net / 12.0,
        effective_tax_rate=eff_rate,
    )


def get_paula_presets() -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="1. Last Year (Full-Time)",
            category="Paula",
            employment_income=91610.75,
            age=63,
            is_working=True,
            pssa_rate=5498.83 / 91610.75,
            union_rate=1490.28 / 91610.75,
        ),
        ScenarioInput(
            name="2. Continue Work (4-Day + CPP)",
            category="Paula",
            employment_income=69006.00,
            cpp_income=17280.00,
            age=64,
            is_working=True,
            pssa_rate=5498.83 / 91610.75,
            union_rate=1490.28 / 91610.75,
        ),
        ScenarioInput(
            name="3. Retire @ 64 (Pension + CPP)",
            category="Paula",
            pension_income=37200.00,
            cpp_income=17280.00,
            age=64,
            is_working=False,
        ),
        ScenarioInput(
            name="4. Retire @ 64 + $15k RRSP",
            category="Paula",
            pension_income=37200.00,
            cpp_income=17280.00,
            rrsp_withdrawal=15000.00,
            age=64,
            is_working=False,
        ),
        ScenarioInput(
            name="5. Retire 2027 @ 65 (+ OAS)",
            category="Paula",
            pension_income=37944.00,
            cpp_income=17625.00,
            oas_income=7334.64,
            age=65,
            is_working=False,
        ),
    ]


def get_randy_presets() -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="1. IT-03 Full-Time (100%)",
            category="Randy",
            employment_income=114200.00,
            age=61,
            is_working=True,
            pssa_rate=0.092,
            union_rate=0.011,
            sdb_annual=230.00,
        ),
        ScenarioInput(
            name="2. PRTL 4-Day (80%)",
            category="Randy",
            employment_income=91360.00,
            age=61,
            is_working=True,
            pssa_rate=0.092,
            union_rate=0.011,
            sdb_annual=230.00,
        ),
        ScenarioInput(
            name="3. PRTL 3-Day (60%)",
            category="Randy",
            employment_income=68520.00,
            age=61,
            is_working=True,
            pssa_rate=0.092,
            union_rate=0.011,
            sdb_annual=230.00,
        ),
        ScenarioInput(
            name="4. Full Retirement (Pension)",
            category="Randy",
            pension_income=64800.00,
            age=62,
            is_working=False,
            health_dental_benefits=1450.00,
            sdb_annual=230.00,
        ),
    ]


def print_comparison_table(results: List[TaxAndNetResult], title: str):
    print("\n" + "=" * 115)
    print(f" {title.upper()}")
    print("=" * 115)

    col_w = 18
    label_w = 26

    header = f"{'Metric':<{label_w}}" + "".join(
        f"{r.name[:col_w-1]:>{col_w}}" for r in results
    )
    print(header)
    print("-" * 115)

    rows = [
        ("Annual Gross Income", [f"${r.gross_income:,.2f}" for r in results]),
        (
            "PSSA Pension Ded.",
            [f"-${r.pssa_deduction:,.2f}" for r in results],
        ),
        ("Union Dues", [f"-${r.union_dues:,.2f}" for r in results]),
        ("CPP Contributions", [f"-${r.cpp_deduction:,.2f}" for r in results]),
        ("EI Premiums", [f"-${r.ei_deduction:,.2f}" for r in results]),
        ("Federal Tax (Net)", [f"-${r.fed_tax_net:,.2f}" for r in results]),
        (
            "Provincial Tax + OHP",
            [f"-${r.prov_tax_net:,.2f}" for r in results],
        ),
        ("TOTAL TAX PAID", [f"-${r.total_tax:,.2f}" for r in results]),
        (
            "Effective Tax Rate",
            [f"{r.effective_tax_rate:.1f}%" for r in results],
        ),
        (
            "Other (Benefits/SDB)",
            [f"-${r.other_deductions:,.2f}" for r in results],
        ),
        ("-" * 24, ["-" * (col_w - 2) for _ in results]),
        ("ANNUAL NET TAKE-HOME", [f"${r.annual_net_cash:,.2f}" for r in results]),
        ("MONTHLY NET CASH", [f"${r.monthly_net_cash:,.2f}" for r in results]),
        ("BI-WEEKLY NET PAY", [f"${r.biweekly_net_cash:,.2f}" for r in results]),
    ]

    for label, vals in rows:
        print(f"{label:<{label_w}}" + "".join(f"{v:>{col_w}}" for v in vals))
    print("=" * 115 + "\n")


def export_to_csv(results: List[TaxAndNetResult], filename: str):
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Scenario",
            "Gross Income",
            "PSSA Pension",
            "Union Dues",
            "CPP",
            "EI",
            "Federal Net Tax",
            "Provincial Net Tax + OHP",
            "Total Tax",
            "Effective Tax %",
            "Other Deductions",
            "Annual Net Cash",
            "Monthly Net Cash",
            "Bi-Weekly Net Cash",
        ])
        for r in results:
            writer.writerow([
                r.name,
                f"{r.gross_income:.2f}",
                f"{r.pssa_deduction:.2f}",
                f"{r.union_dues:.2f}",
                f"{r.cpp_deduction:.2f}",
                f"{r.ei_deduction:.2f}",
                f"{r.fed_tax_net:.2f}",
                f"{r.prov_tax_net:.2f}",
                f"{r.total_tax:.2f}",
                f"{r.effective_tax_rate:.2f}",
                f"{r.other_deductions:.2f}",
                f"{r.annual_net_cash:.2f}",
                f"{r.monthly_net_cash:.2f}",
                f"{r.biweekly_net_cash:.2f}",
            ])
    print(f"-> Exported results to: {os.path.abspath(filename)}")


def prompt_float(prompt_text: str, default: float) -> float:
    raw = input(f"{prompt_text} [Default: {default}]: ").strip()
    if not raw:
        return default
    try:
        return float(raw.replace("$", "").replace(",", ""))
    except ValueError:
        print("Invalid number, using default.")
        return default


def run_custom_sandbox():
    print("\n--- CUSTOM INTERACTIVE RETIREMENT / SHIFT SANDBOX ---")
    name = (
        input("Scenario Name [Default: Custom Scenario]: ").strip()
        or "Custom Scenario"
    )
    age = int(prompt_float("Age during this tax year", 64))
    working_str = (
        input("Are you still working in this scenario? (y/n) [Default: y]: ")
        .strip()
        .lower()
    )
    is_working = working_str != "n"

    emp_income = 0.0
    if is_working:
        mode = (
            input(
                "Enter employment income by (1) Hourly Rate & Shifts or (2)"
                " Annual Gross? [1/2, Default: 1]: "
            )
            .strip()
        )
        if mode == "2":
            emp_income = prompt_float("Annual Employment Gross ($)", 69006.0)
        else:
            hourly = prompt_float("Hourly Rate ($/hr)", 58.98)
            shift_len = prompt_float("Hours per Shift", 11.25)
            shifts_biweekly = prompt_float(
                "Shifts per 2 Weeks (e.g., 4 or 3)", 4.0
            )
            emp_income = hourly * shift_len * shifts_biweekly * 26.0
            print(
                "   -> Calculated Annual Employment Gross (26 pays):"
                f" ${emp_income:,.2f}"
            )

    pension = prompt_float(
        "Annual Public Service / Employer Pension ($)",
        0.0 if is_working else 37200.0,
    )
    cpp = prompt_float("Annual CPP Income ($)", 17280.0)
    oas = prompt_float("Annual OAS Income ($)", 0.0 if age < 65 else 7334.64)
    rrsp = prompt_float("Annual RRSP Withdrawal ($)", 0.0)
    benefits = prompt_float(
        "Annual Retiree Health/Dental/SDB Deductions ($)", 0.0
    )

    custom = ScenarioInput(
        name=name,
        category="Custom",
        employment_income=emp_income,
        pension_income=pension,
        cpp_income=cpp,
        oas_income=oas,
        rrsp_withdrawal=rrsp,
        age=age,
        is_working=is_working,
        health_dental_benefits=benefits,
    )
    res = calculate_2026_ontario_tax_and_net(custom)
    print_comparison_table([res], f"Custom Simulation: {name}")


def main():
    while True:
        print("\n=======================================================")
        print(" CANADIAN RETIREMENT & NET CASH FLOW CALCULATOR (2026)")
        print("=======================================================")
        print("1. View Paula's Scenarios (CalcPaula Comparison Table)")
        print("2. View Randy's Scenarios (GoC IT-03 / PRTL Comparison)")
        print("3. Run Custom Interactive Scenario (Hourly/Shifts/Pension/RRSP)")
        print("4. Export Both Paula & Randy Scenarios to CSV")
        print("5. Exit")
        choice = input("\nSelect an option (1-5): ").strip()

        if choice == "1":
            results = [
                calculate_2026_ontario_tax_and_net(s)
                for s in get_paula_presets()
            ]
            print_comparison_table(
                results, "Paula's Retirement & Shift Scenarios (2026 Ontario)"
            )
        elif choice == "2":
            results = [
                calculate_2026_ontario_tax_and_net(s)
                for s in get_randy_presets()
            ]
            print_comparison_table(
                results,
                "Randy's GoC Retirement & PRTL Scenarios (2026 Ontario)",
            )
        elif choice == "3":
            run_custom_sandbox()
        elif choice == "4":
            paula_res = [
                calculate_2026_ontario_tax_and_net(s)
                for s in get_paula_presets()
            ]
            randy_res = [
                calculate_2026_ontario_tax_and_net(s)
                for s in get_randy_presets()
            ]
            export_to_csv(paula_res, "paula_retirement_scenarios.csv")
            export_to_csv(randy_res, "randy_retirement_scenarios.csv")
        elif choice == "5":
            print(
                "Exiting calculator. Good luck with the retirement planning!"
            )
            break
        else:
            print("Invalid selection. Please enter 1-5.")


if __name__ == "__main__":
    main()