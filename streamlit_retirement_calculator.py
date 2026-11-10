"""
Streamlit Ontario Retirement & Payroll Calculator
------------------------------------------------
Comprehensive tax, pension, and payroll modeling engine for Ontario residents.
Features:
- Multi-year scenario comparison (Active vs. Retired / Pinned scenarios)
- Flat-schema JSON threshold loading (`tax_thresholds.json`) with CPI indexation
- Full support for T4 overrides (Box 16/16A CPP, Box 18 EI, Box 20 RPP, Box 22 Tax, Box 44 Union Dues)
- Progressive Federal & Ontario tax calculation with full brackets
- Non-refundable tax credits (BPA, CPP/EI, Pension Income Credit, Age Credit with clawback)
- Ontario Surtax and stepped Ontario Health Premium (OHP)
- Interactive Threshold Viewer tab synced directly to the flat JSON schema
"""

import streamlit as st
import pandas as pd
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Page Configuration & Branding
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Canadian Retirement Calculator (Ontario)",
    page_icon="ON_LOGO_W-01-03.png" if os.path.exists("ON_LOGO_W-01-03.png") else "🍁",
    layout="wide"
)

# ---------------------------------------------------------------------------
# Default / Fallback Thresholds (Flat Schema)
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "2025": {
        "is_projected": False,
        "default_indexation_rate": 0.027,
        "cpp_basic_exemption": 3500.0,
        "ympe": 71300.0,
        "cpp1_rate": 0.0595,
        "yampe": 81200.0,
        "cpp2_rate": 0.0400,
        "ei_rate": 0.0164,
        "ei_max_premium": 1077.48,
        "federal_bpa": 16129.0,
        "ontario_bpa": 12747.0,
        "fed_age_amount": 9028.0,
        "fed_age_threshold": 45522.0,
        "ont_age_amount": 6223.0,
        "ont_age_threshold": 46330.0,
        "fed_pension_max": 2000.0,
        "ont_pension_max": 1714.0,
        "ont_surtax_t1": 5710.0,
        "ont_surtax_t2": 7307.0,
        "federal_brackets": [
            {"threshold": 57375, "rate": 0.15},
            {"threshold": 114750, "rate": 0.205},
            {"threshold": 177882, "rate": 0.26},
            {"threshold": 253414, "rate": 0.29},
            {"threshold": 999999999, "rate": 0.33}
        ],
        "ontario_brackets": [
            {"threshold": 52886, "rate": 0.0505},
            {"threshold": 105775, "rate": 0.0915},
            {"threshold": 150000, "rate": 0.1116},
            {"threshold": 220000, "rate": 0.1216},
            {"threshold": 999999999, "rate": 0.1316}
        ]
    },
    "2026": {
        "is_projected": False,
        "default_indexation_rate": 0.020,
        "cpp_basic_exemption": 3500.0,
        "ympe": 74600.0,
        "cpp1_rate": 0.0595,
        "yampe": 85000.0,
        "cpp2_rate": 0.0400,
        "ei_rate": 0.0163,
        "ei_max_premium": 1123.07,
        "federal_bpa": 16452.0,
        "ontario_bpa": 12989.0,
        "fed_age_amount": 9208.0,
        "fed_age_threshold": 46432.0,
        "ont_age_amount": 6351.0,
        "ont_age_threshold": 47210.0,
        "fed_pension_max": 2000.0,
        "ont_pension_max": 1747.0,
        "ont_surtax_t1": 5818.0,
        "ont_surtax_t2": 7446.0,
        "federal_brackets": [
            {"threshold": 58523, "rate": 0.14},
            {"threshold": 117045, "rate": 0.205},
            {"threshold": 181440, "rate": 0.26},
            {"threshold": 258482, "rate": 0.29},
            {"threshold": 999999999, "rate": 0.33}
        ],
        "ontario_brackets": [
            {"threshold": 53891, "rate": 0.0505},
            {"threshold": 107785, "rate": 0.0915},
            {"threshold": 150000, "rate": 0.1116},
            {"threshold": 220000, "rate": 0.1216},
            {"threshold": 999999999, "rate": 0.1316}
        ]
    },
    "2027": {
        "is_projected": True,
        "default_indexation_rate": 0.026,
        "cpp_basic_exemption": 3500.0,
        "ympe": 76700.0,
        "cpp1_rate": 0.0595,
        "yampe": 87400.0,
        "cpp2_rate": 0.0400,
        "ei_rate": 0.0163,
        "ei_max_premium": 1152.27,
        "federal_bpa": 16880.0,
        "ontario_bpa": 13325.0,
        "fed_age_amount": 9447.0,
        "fed_age_threshold": 47639.0,
        "ont_age_amount": 6516.0,
        "ont_age_threshold": 48437.0,
        "fed_pension_max": 2000.0,
        "ont_pension_max": 1792.0,
        "ont_surtax_t1": 5969.0,
        "ont_surtax_t2": 7640.0,
        "federal_brackets": [
            {"threshold": 60045, "rate": 0.14},
            {"threshold": 120088, "rate": 0.205},
            {"threshold": 186157, "rate": 0.26},
            {"threshold": 265203, "rate": 0.29},
            {"threshold": 999999999, "rate": 0.33}
        ],
        "ontario_brackets": [
            {"threshold": 55292, "rate": 0.0505},
            {"threshold": 110587, "rate": 0.0915},
            {"threshold": 150000, "rate": 0.1116},
            {"threshold": 220000, "rate": 0.1216},
            {"threshold": 999999999, "rate": 0.1316}
        ]
    }
}

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
@dataclass
class ScenarioInput:
    name: str
    tax_year: str
    age: int = 60
    indexation_rate: float = 0.026

    # Income Streams
    employment_income: float = 0.0
    pension_income: float = 0.0
    cpp_income: float = 0.0
    oas_income: float = 0.0
    rrsp_withdrawal: float = 0.0

    # T4 Payroll & Deductions
    t4_box20_rpp: float = 0.0
    t4_box44_union: float = 0.0
    t4_box16_cpp1: float = 0.0
    t4_box16_cpp2: float = 0.0
    t4_box18_ei: float = 0.0
    t4_box22_tax_deducted: float = 0.0

    # Personal & Work Expenses
    health_dental_benefits: float = 0.0
    exp_bus: float = 0.0
    exp_lunch: float = 0.0
    exp_parking: float = 0.0
    exp_fuel: float = 0.0
    exp_lottery: float = 0.0
    exp_other: float = 0.0
    work_expenses: float = 0.0
    sdb_annual: float = 0.0


@dataclass
class TaxAndNetResult:
    name: str
    tax_year: str
    gross_income: float

    pssa_deduction: float
    union_dues: float

    cpp1_deduction: float
    cpp2_deduction: float
    cpp_deduction: float
    ei_deduction: float

    taxable_income: float

    fed_tax_gross: float
    prov_tax_gross: float

    fed_bpa_credit_amt: float
    prov_bpa_credit_amt: float

    fed_pension_credit_amt: float
    prov_pension_credit_amt: float

    fed_age_credit_amt: float
    prov_age_credit_amt: float
    fed_age_clawback_amt: float

    total_fed_credits: float
    total_prov_credits: float
    total_credits_savings: float

    fed_tax_net: float
    prov_basic_net: float

    ontario_surtax: float
    health_premium: float
    prov_tax_net: float

    total_tax: float

    other_deductions: float
    total_deductions: float

    annual_net_cash: float
    biweekly_net_cash: float
    monthly_net_cash: float

    effective_tax_rate: float

    fed_steps: List[str] = field(default_factory=list)
    prov_steps: List[str] = field(default_factory=list)
    credit_steps: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JSON Loader
# ---------------------------------------------------------------------------
def load_thresholds_db(filepath: str = "tax_thresholds.json") -> Dict[str, Any]:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so missing years/keys always have safe fallbacks
        merged = {**DEFAULT_THRESHOLDS}
        for yr, vals in data.items():
            if yr in merged:
                merged[yr] = {**merged[yr], **vals}
            else:
                merged[yr] = vals
        return merged
    return DEFAULT_THRESHOLDS


# ---------------------------------------------------------------------------
# Tax & Payroll Calculation Engine
# ---------------------------------------------------------------------------
def calculate_ontario_health_premium(taxable_income: float) -> float:
    """Official stepped Ontario Health Premium (OHP) schedule."""
    if taxable_income <= 20000.0:
        return 0.0
    elif taxable_income <= 25000.0:
        return min(300.0, (taxable_income - 20000.0) * 0.06)
    elif taxable_income <= 36000.0:
        return 300.0
    elif taxable_income <= 38500.0:
        return min(450.0, 300.0 + (taxable_income - 36000.0) * 0.06)
    elif taxable_income <= 48000.0:
        return 450.0
    elif taxable_income <= 48600.0:
        return min(600.0, 450.0 + (taxable_income - 48000.0) * 0.25)
    elif taxable_income <= 72000.0:
        return 600.0
    elif taxable_income <= 72600.0:
        return min(750.0, 600.0 + (taxable_income - 72000.0) * 0.25)
    elif taxable_income <= 200000.0:
        return 750.0
    elif taxable_income <= 200600.0:
        return min(900.0, 750.0 + (taxable_income - 200000.0) * 0.25)
    else:
        return 900.0


def compute_progressive_brackets(
    taxable_income: float,
    brackets: List[Dict[str, float]],
    scale: float
) -> tuple[float, List[str]]:
    """Iterates cleanly over flat JSON bracket dicts: [{'threshold': ..., 'rate': ...}]."""
    gross_tax = 0.0
    steps: List[str] = []
    prev_limit = 0.0

    for idx, b in enumerate(brackets):
        raw_thresh = float(b.get("threshold", 999999999.0))
        rate = float(b.get("rate", 0.0))
        # Do not inflate sentinel top bracket cap
        limit = raw_thresh if raw_thresh >= 900000000.0 else raw_thresh * scale

        if taxable_income <= prev_limit:
            break

        if taxable_income <= limit:
            slice_amt = taxable_income - prev_limit
            tax_part = slice_amt * rate
            gross_tax += tax_part
            cap_label = "Max" if limit >= 900000000.0 else f"${limit:,.0f}"
            steps.append(
                f"Tier {idx+1} (${prev_limit:,.0f} - {cap_label}) @ {rate*100:.2f}%: "
                f"${slice_amt:,.2f} x {rate*100:.2f}% = ${tax_part:,.2f}"
            )
            prev_limit = taxable_income
            break
        else:
            slice_amt = limit - prev_limit
            tax_part = slice_amt * rate
            gross_tax += tax_part
            steps.append(
                f"Tier {idx+1} (${prev_limit:,.0f} - ${limit:,.0f}) @ {rate*100:.2f}%: "
                f"${slice_amt:,.2f} x {rate*100:.2f}% = ${tax_part:,.2f}"
            )
            prev_limit = limit

    if taxable_income > prev_limit and brackets:
        top_rate = float(brackets[-1].get("rate", 0.0))
        slice_amt = taxable_income - prev_limit
        tax_part = slice_amt * top_rate
        gross_tax += tax_part
        steps.append(
            f"Top Tier (Over ${prev_limit:,.0f}) @ {top_rate*100:.2f}%: "
            f"${slice_amt:,.2f} x {top_rate*100:.2f}% = ${tax_part:,.2f}"
        )

    return gross_tax, steps


def calculate_ontario_tax_and_net(s: ScenarioInput, thresholds_db: Dict[str, Any]) -> TaxAndNetResult:
    # Resolve closest available year key in JSON
    if s.tax_year in thresholds_db:
        year_key = s.tax_year
    else:
        available_sorted = sorted(thresholds_db.keys())
        year_key = available_sorted[-1] if available_sorted else "2026"

    y_data = thresholds_db[year_key]

    # Determine projection scaling if requested year is beyond base year or marked projected
    base_yr_int = int(year_key)
    req_yr_int = int(s.tax_year)
    is_projected = y_data.get("is_projected", False) or (req_yr_int > base_yr_int)

    if req_yr_int > base_yr_int:
        years_ahead = req_yr_int - base_yr_int
        scale = (1.0 + s.indexation_rate) ** years_ahead
    elif is_projected:
        default_rate = float(y_data.get("default_indexation_rate", 0.026))
        scale = (1.0 + s.indexation_rate) / (1.0 + default_rate)
    else:
        scale = 1.0

    # 1. Total Gross Income
    gross = (
        s.employment_income
        + s.pension_income
        + s.cpp_income
        + s.oas_income
        + s.rrsp_withdrawal
    )

    # 2. Payroll / Statutory Deductions (with T4 Box Overrides)
    exemption = float(y_data.get("cpp_basic_exemption", 3500.0))
    ympe = float(y_data.get("ympe", 74600.0)) * scale
    yampe = float(y_data.get("yampe", 85000.0)) * scale
    cpp1_rate = float(y_data.get("cpp1_rate", 0.0595))
    cpp2_rate = float(y_data.get("cpp2_rate", 0.0400))

    ei_rate = float(y_data.get("ei_rate", 0.0163))
    ei_max = float(y_data.get("ei_max_premium", 1123.07)) * scale

    cpp1 = (
        s.t4_box16_cpp1
        if s.t4_box16_cpp1 > 0
        else round(max(0.0, min(s.employment_income, ympe) - exemption) * cpp1_rate, 2)
    )
    cpp2 = (
        s.t4_box16_cpp2
        if s.t4_box16_cpp2 > 0
        else round(max(0.0, min(s.employment_income, yampe) - ympe) * cpp2_rate, 2)
    )
    ei = (
        s.t4_box18_ei
        if s.t4_box18_ei > 0
        else round(min(s.employment_income * ei_rate, ei_max), 2)
    )

    pssa_deduction = s.t4_box20_rpp
    union_dues = s.t4_box44_union

    # 3. Taxable Income
    taxable_income = max(0.0, gross - pssa_deduction - union_dues)

    # 4. Progressive Federal & Ontario Gross Taxes
    fed_brackets = y_data.get("federal_brackets", [])
    ont_brackets = y_data.get("ontario_brackets", [])

    fed_gross, fed_steps = compute_progressive_brackets(taxable_income, fed_brackets, scale)
    prov_gross, prov_steps = compute_progressive_brackets(taxable_income, ont_brackets, scale)

    fed_lowest_rate = float(fed_brackets[0]["rate"]) if fed_brackets else 0.14
    ont_lowest_rate = float(ont_brackets[0]["rate"]) if ont_brackets else 0.0505

    # 5. Non-Refundable Tax Credits
    credit_steps: List[str] = []

    # Basic Personal Amount (BPA)
    fed_bpa_base = float(y_data.get("federal_bpa", 16452.0)) * scale
    ont_bpa_base = float(y_data.get("ontario_bpa", 12989.0)) * scale
    fed_bpa_credit = fed_bpa_base * fed_lowest_rate
    ont_bpa_credit = ont_bpa_base * ont_lowest_rate
    credit_steps.append(f"Federal BPA: ${fed_bpa_base:,.2f} x {fed_lowest_rate*100:.2f}% = ${fed_bpa_credit:,.2f}")
    credit_steps.append(f"Ontario BPA: ${ont_bpa_base:,.2f} x {ont_lowest_rate*100:.2f}% = ${ont_bpa_credit:,.2f}")

    # CPP / EI Contributions Credit
    fed_cpp_ei_credit = (cpp1 + cpp2 + ei) * fed_lowest_rate
    ont_cpp_ei_credit = (cpp1 + cpp2 + ei) * ont_lowest_rate
    credit_steps.append(f"Federal CPP/EI Credit: ${(cpp1+cpp2+ei):,.2f} x {fed_lowest_rate*100:.2f}% = ${fed_cpp_ei_credit:,.2f}")
    credit_steps.append(f"Ontario CPP/EI Credit: ${(cpp1+cpp2+ei):,.2f} x {ont_lowest_rate*100:.2f}% = ${ont_cpp_ei_credit:,.2f}")

    # Pension Income Credit (Eligible RPP / Pension income)
    fed_pension_max = float(y_data.get("fed_pension_max", 2000.0))
    ont_pension_max = float(y_data.get("ont_pension_max", 1747.0)) * scale
    fed_pension_credit_amt = min(s.pension_income, fed_pension_max) * fed_lowest_rate
    prov_pension_credit_amt = min(s.pension_income, ont_pension_max) * ont_lowest_rate
    if s.pension_income > 0:
        credit_steps.append(f"Federal Pension Credit: ${min(s.pension_income, fed_pension_max):,.2f} x {fed_lowest_rate*100:.2f}% = ${fed_pension_credit_amt:,.2f}")
        credit_steps.append(f"Ontario Pension Credit: ${min(s.pension_income, ont_pension_max):,.2f} x {ont_lowest_rate*100:.2f}% = ${prov_pension_credit_amt:,.2f}")

    # Age Credit (65+ with 15% clawback above net income threshold)
    fed_age_credit_amt = 0.0
    prov_age_credit_amt = 0.0
    fed_age_clawback_amt = 0.0
    if s.age >= 65:
        fed_age_max = float(y_data.get("fed_age_amount", 9208.0)) * scale
        fed_age_thresh = float(y_data.get("fed_age_threshold", 46432.0)) * scale
        fed_age_clawback_amt = max(0.0, (taxable_income - fed_age_thresh) * 0.15)
        fed_age_eligible = max(0.0, fed_age_max - fed_age_clawback_amt)
        fed_age_credit_amt = fed_age_eligible * fed_lowest_rate

        ont_age_max = float(y_data.get("ont_age_amount", 6351.0)) * scale
        ont_age_thresh = float(y_data.get("ont_age_threshold", 47210.0)) * scale
        ont_age_clawback = max(0.0, (taxable_income - ont_age_thresh) * 0.15)
        ont_age_eligible = max(0.0, ont_age_max - ont_age_clawback)
        prov_age_credit_amt = ont_age_eligible * ont_lowest_rate

        credit_steps.append(f"Federal Age Credit (Net of Clawback): ${fed_age_credit_amt:,.2f}")
        credit_steps.append(f"Ontario Age Credit (Net of Clawback): ${prov_age_credit_amt:,.2f}")

    total_fed_credits = fed_bpa_credit + fed_cpp_ei_credit + fed_pension_credit_amt + fed_age_credit_amt
    total_prov_credits = ont_bpa_credit + ont_cpp_ei_credit + prov_pension_credit_amt + prov_age_credit_amt

    # 6. Net Federal Tax & Basic Provincial Tax
    fed_tax_net = max(0.0, fed_gross - total_fed_credits)
    prov_basic_net = max(0.0, prov_gross - total_prov_credits)

    # 7. Ontario Surtax (20% over T1 + 36% over T2)
    surtax_t1 = float(y_data.get("ont_surtax_t1", 5818.0)) * scale
    surtax_t2 = float(y_data.get("ont_surtax_t2", 7446.0)) * scale
    ontario_surtax = 0.0
    if prov_basic_net > surtax_t1:
        ontario_surtax += (prov_basic_net - surtax_t1) * 0.20
    if prov_basic_net > surtax_t2:
        ontario_surtax += (prov_basic_net - surtax_t2) * 0.36

    # 8. Ontario Health Premium (OHP)
    health_premium = calculate_ontario_health_premium(taxable_income)

    prov_tax_total = prov_basic_net + ontario_surtax + health_premium
    calculated_total_tax = fed_tax_net + prov_tax_total

    # Honor T4 Box 22 Tax Deducted Override if provided
    if s.t4_box22_tax_deducted > 0:
        total_tax = s.t4_box22_tax_deducted
    else:
        total_tax = calculated_total_tax

    # 9. Net Cash Flow & Deductions Summary
    other_deductions = (
        s.health_dental_benefits
        + s.exp_bus
        + s.exp_lunch
        + s.exp_parking
        + s.exp_fuel
        + s.exp_lottery
        + s.exp_other
        + s.work_expenses
        + s.sdb_annual
    )

    total_deductions = (
        pssa_deduction
        + union_dues
        + cpp1
        + cpp2
        + ei
        + total_tax
        + other_deductions
    )

    annual_net_cash = gross - total_deductions
    biweekly_net_cash = annual_net_cash / 26.0
    monthly_net_cash = annual_net_cash / 12.0
    effective_tax_rate = (total_tax / gross * 100.0) if gross > 0 else 0.0

    return TaxAndNetResult(
        name=s.name,
        tax_year=s.tax_year,
        gross_income=gross,
        pssa_deduction=pssa_deduction,
        union_dues=union_dues,
        cpp1_deduction=cpp1,
        cpp2_deduction=cpp2,
        cpp_deduction=cpp1 + cpp2,
        ei_deduction=ei,
        taxable_income=taxable_income,
        fed_tax_gross=fed_gross,
        prov_tax_gross=prov_gross,
        fed_bpa_credit_amt=fed_bpa_credit,
        prov_bpa_credit_amt=ont_bpa_credit,
        fed_pension_credit_amt=fed_pension_credit_amt,
        prov_pension_credit_amt=prov_pension_credit_amt,
        fed_age_credit_amt=fed_age_credit_amt,
        prov_age_credit_amt=prov_age_credit_amt,
        fed_age_clawback_amt=fed_age_clawback_amt,
        total_fed_credits=total_fed_credits,
        total_prov_credits=total_prov_credits,
        total_credits_savings=total_fed_credits + total_prov_credits,
        fed_tax_net=fed_tax_net,
        prov_basic_net=prov_basic_net,
        ontario_surtax=ontario_surtax,
        health_premium=health_premium,
        prov_tax_net=prov_tax_total,
        total_tax=total_tax,
        other_deductions=other_deductions,
        total_deductions=total_deductions,
        annual_net_cash=annual_net_cash,
        biweekly_net_cash=biweekly_net_cash,
        monthly_net_cash=monthly_net_cash,
        effective_tax_rate=effective_tax_rate,
        fed_steps=fed_steps,
        prov_steps=prov_steps,
        credit_steps=credit_steps
    )


# ---------------------------------------------------------------------------
# Comparison Table Builder
# ---------------------------------------------------------------------------
def build_comparison_dataframe(results: List[TaxAndNetResult]) -> pd.DataFrame:
    metrics = [
        ("Tax Year Threshold Engine", [r.tax_year for r in results]),
        ("Annual Gross Income", [f"${r.gross_income:,.2f}" for r in results]),
        ("PSSA Pension Contribution (Box 20 RPP)", [f"-${r.pssa_deduction:,.2f}" for r in results]),
        ("Union Dues (Box 44)", [f"-${r.union_dues:,.2f}" for r in results]),
        ("CPP1 Contributions - Base (Box 16)", [f"-${r.cpp1_deduction:,.2f}" for r in results]),
        ("CPP2 Contributions - Additional (Box 16A)", [f"-${r.cpp2_deduction:,.2f}" for r in results]),
        ("EI Premiums (Box 18)", [f"-${r.ei_deduction:,.2f}" for r in results]),
        ("Taxable Income", [f"${r.taxable_income:,.2f}" for r in results]),
        ("Federal BPA Credit", [f"-${r.fed_bpa_credit_amt:,.2f}" for r in results]),
        ("Ontario BPA Credit", [f"-${r.prov_bpa_credit_amt:,.2f}" for r in results]),
        ("Federal Pension Credit", [f"-${r.fed_pension_credit_amt:,.2f}" for r in results]),
        ("Ontario Pension Credit", [f"-${r.prov_pension_credit_amt:,.2f}" for r in results]),
        ("Federal Age Credit (Net of Clawback)", [f"-${r.fed_age_credit_amt:,.2f}" for r in results]),
        ("Ontario Age Credit", [f"-${r.prov_age_credit_amt:,.2f}" for r in results]),
        ("Total Tax Savings from Credits", [f"-${r.total_credits_savings:,.2f}" for r in results]),
        ("Federal Income Tax (Net)", [f"${r.fed_tax_net:,.2f}" for r in results]),
        ("Provincial Income Tax (Basic Net)", [f"${r.prov_basic_net:,.2f}" for r in results]),
        ("Ontario Surtax", [f"${r.ontario_surtax:,.2f}" for r in results]),
        ("Ontario Health Premium (OHP)", [f"${r.health_premium:,.2f}" for r in results]),
        ("Provincial Tax (Total incl. Surtax & OHP)", [f"${r.prov_tax_net:,.2f}" for r in results]),
        ("TOTAL ANNUAL TAX PAID", [f"-${r.total_tax:,.2f}" for r in results]),
        ("Effective Tax Rate (%)", [f"{r.effective_tax_rate:.2f}%" for r in results]),
        ("Other Expenses (Benefits/Bus/Lunch/Fuel/etc.)", [f"-${r.other_deductions:,.2f}" for r in results]),
        ("TOTAL ANNUAL DEDUCTIONS & EXPENSES", [f"-${r.total_deductions:,.2f}" for r in results]),
        ("ANNUAL NET TAKE-HOME PAY", [f"${r.annual_net_cash:,.2f}" for r in results]),
        ("MONTHLY NET CASH FLOW", [f"${r.monthly_net_cash:,.2f}" for r in results]),
        ("BI-WEEKLY NET PAYCHEQUE", [f"${r.biweekly_net_cash:,.2f}" for r in results]),
    ]

    df_dict = {"Financial / Tax Line Item": [m[0] for m in metrics]}
    for idx, r in enumerate(results):
        col_title = f"{r.name} ({r.tax_year})"
        if col_title in df_dict:
            col_title = f"{col_title} #{idx+1}"
        df_dict[col_title] = [m[1][idx] for m in metrics]

    return pd.DataFrame(df_dict)


# ---------------------------------------------------------------------------
# Main Application UI
# ---------------------------------------------------------------------------
def main():
    thresholds_db = load_thresholds_db("tax_thresholds.json")

    if "pinned_scenarios" not in st.session_state:
        st.session_state["pinned_scenarios"] = []

    # Header
    h_col1, h_col2 = st.columns([1, 6])
    with h_col1:
        if os.path.exists("ON_LOGO_W-01-03.png"):
            st.image("ON_LOGO_W-01-03.png", width=110)
    with h_col2:
        st.title("Ontario Retirement & Payroll Calculator")
        st.caption("Data-driven Canadian & Ontario tax, pension, and payroll modeling engine.")

    tab_calc, tab_thresh, tab_json = st.tabs([
        "📊 Scenario Comparison & Sandbox",
        "📋 Tax Threshold Viewer",
        "⚙️ JSON Configuration Editor"
    ])

    # =========================================================================
    # TAB 1: SCENARIO COMPARISON & SANDBOX
    # =========================================================================
    with tab_calc:
        sb_left, sb_right = st.columns([1, 2.3], gap="large")

        with sb_left:
            st.subheader("1. Scenario Configuration")
            scen_name = st.text_input("Scenario Label", value="Working (2026)")

            year_options = [str(y) for y in range(2020, 2036)]
            default_idx = year_options.index("2026") if "2026" in year_options else 0
            tax_year = st.selectbox("Tax Year", year_options, index=default_idx)

            y_meta = thresholds_db.get(tax_year, thresholds_db.get("2026", {}))
            is_proj = y_meta.get("is_projected", int(tax_year) > 2026)
            default_cpi = float(y_meta.get("default_indexation_rate", 0.026)) * 100.0

            if is_proj:
                st.info(f"🔮 **{tax_year}** uses CPI projection scaling.")
            else:
                st.success(f"🔒 **{tax_year}** uses official threshold figures.")

            indexation_rate = st.slider(
                "CPI / Indexation Rate (%)",
                min_value=0.0,
                max_value=6.0,
                value=default_cpi,
                step=0.1
            ) / 100.0

            age = st.number_input("Age in Tax Year (65+ triggers Age Credits)", min_value=18, max_value=105, value=60)

            with st.expander("💰 Income Streams", expanded=True):
                emp_inc = st.number_input("Employment Income (T4 Box 14) [$]", min_value=0.0, value=91610.75, step=500.0)
                pen_inc = st.number_input("RPP / Pension Income [$]", min_value=0.0, value=0.0, step=500.0)
                cpp_inc = st.number_input("CPP Retirement Benefit [$]", min_value=0.0, value=0.0, step=250.0)
                oas_inc = st.number_input("OAS Pension [$]", min_value=0.0, value=0.0, step=250.0)
                rrsp_inc = st.number_input("RRSP / RRIF Withdrawal [$]", min_value=0.0, value=0.0, step=500.0)

            with st.expander("🧾 T4 Payroll Deductions & Overrides", expanded=True):
                box20_rpp = st.number_input("PSSA / RPP Contribution (Box 20) [$]", min_value=0.0, value=5498.83, step=100.0)
                box44_union = st.number_input("Union Dues (Box 44) [$]", min_value=0.0, value=1490.28, step=50.0)
                box16_cpp1 = st.number_input("Override CPP1 (Box 16) [0 = Auto]", min_value=0.0, value=0.0, step=50.0)
                box16_cpp2 = st.number_input("Override CPP2 (Box 16A) [0 = Auto]", min_value=0.0, value=0.0, step=25.0)
                box18_ei = st.number_input("Override EI (Box 18) [0 = Auto]", min_value=0.0, value=0.0, step=25.0)
                box22_tax = st.number_input("Override Total Tax (Box 22) [0 = Auto]", min_value=0.0, value=0.0, step=250.0)

            with st.expander("💳 Personal & Work Expenses", expanded=False):
                health_ben = st.number_input("Health / Dental Benefits [$]", min_value=0.0, value=0.0, step=50.0)
                exp_bus = st.number_input("Transit / Bus Pass [$]", min_value=0.0, value=1200.0, step=50.0)
                exp_lunch = st.number_input("Work Lunches / Coffee [$]", min_value=0.0, value=1000.0, step=50.0)
                exp_parking = st.number_input("Parking [$]", min_value=0.0, value=0.0, step=50.0)
                exp_fuel = st.number_input("Commute Fuel [$]", min_value=0.0, value=1000.0, step=50.0)
                exp_lottery = st.number_input("Office Pool / Lottery [$]", min_value=0.0, value=253.0, step=10.0)
                exp_other = st.number_input("Other Personal Expenses [$]", min_value=0.0, value=300.0, step=50.0)
                work_exp = st.number_input("Work Expenses [$]", min_value=0.0, value=0.0, step=50.0)
                sdb_ann = st.number_input("Supplementary Death Benefit (SDB) [$]", min_value=0.0, value=0.0, step=25.0)

            active_input = ScenarioInput(
                name=scen_name,
                tax_year=tax_year,
                age=age,
                indexation_rate=indexation_rate,
                employment_income=emp_inc,
                pension_income=pen_inc,
                cpp_income=cpp_inc,
                oas_income=oas_inc,
                rrsp_withdrawal=rrsp_inc,
                t4_box20_rpp=box20_rpp,
                t4_box44_union=box44_union,
                t4_box16_cpp1=box16_cpp1,
                t4_box16_cpp2=box16_cpp2,
                t4_box18_ei=box18_ei,
                t4_box22_tax_deducted=box22_tax,
                health_dental_benefits=health_ben,
                exp_bus=exp_bus,
                exp_lunch=exp_lunch,
                exp_parking=exp_parking,
                exp_fuel=exp_fuel,
                exp_lottery=exp_lottery,
                exp_other=exp_other,
                work_expenses=work_exp,
                sdb_annual=sdb_ann
            )

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("📌 Pin Scenario", use_container_width=True):
                    st.session_state["pinned_scenarios"].append(active_input)
                    st.toast(f"Pinned '{scen_name}'!")
            with btn_c2:
                if st.button("🗑️ Clear Pinned", use_container_width=True):
                    st.session_state["pinned_scenarios"] = []
                    st.toast("Cleared all pinned scenarios.")

        with sb_right:
            active_res = calculate_ontario_tax_and_net(active_input, thresholds_db)
            all_sb_results = [active_res] + [
                calculate_ontario_tax_and_net(p, thresholds_db)
                for p in st.session_state["pinned_scenarios"]
            ]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gross Income", f"${active_res.gross_income:,.2f}")
            m2.metric("Total Annual Tax", f"${active_res.total_tax:,.2f}", f"{active_res.effective_tax_rate:.2f}% Eff.")
            m3.metric("Annual Net Pay", f"${active_res.annual_net_cash:,.2f}")
            m4.metric("Bi-Weekly Net", f"${active_res.biweekly_net_cash:,.2f}")

            st.subheader("Side-by-Side Financial & Tax Comparison")
            comp_df = build_comparison_dataframe(all_sb_results)
            st.dataframe(comp_df, use_container_width=True, hide_index=True, height=620)

            with st.expander("🔍 Detailed Step-by-Step Tax & Credit Audit (Active Scenario)"):
                st.markdown("**Federal Progressive Tax Breakdown:**")
                for step in active_res.fed_steps:
                    st.text(f"  • {step}")
                st.markdown("**Ontario Provincial Tax Breakdown:**")
                for step in active_res.prov_steps:
                    st.text(f"  • {step}")
                st.markdown("**Applied Non-Refundable Tax Credits:**")
                for step in active_res.credit_steps:
                    st.text(f"  • {step}")

    # =========================================================================
    # TAB 2: TAX THRESHOLD VIEWER (Synced to Flat JSON Schema)
    # =========================================================================
    with tab_thresh:
        st.subheader("Statutory Thresholds & Tax Brackets Inspector")
        avail_db_years = sorted(thresholds_db.keys())
        view_year = st.selectbox("Select Configured Year to Inspect", avail_db_years, index=len(avail_db_years)-1)
        y_info = thresholds_db[view_year]

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CPP YMPE", f"${float(y_info.get('ympe', 0)):,.2f}")
        k2.metric("CPP2 YAMPE", f"${float(y_info.get('yampe', 0)):,.2f}")
        k3.metric("Federal BPA", f"${float(y_info.get('federal_bpa', 0)):,.2f}")
        k4.metric("Ontario BPA", f"${float(y_info.get('ontario_bpa', 0)):,.2f}")

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("### 🇨🇦 Federal Tax Brackets")
            fed_b_list = y_info.get("federal_brackets", [])
            if fed_b_list:
                df_fed = pd.DataFrame([
                    {
                        "Upper Threshold": "No Upper Limit" if b["threshold"] >= 900000000 else f"${b['threshold']:,.2f}",
                        "Marginal Rate": f"{b['rate']*100:.2f}%"
                    }
                    for b in fed_b_list
                ])
                st.table(df_fed)

        with t_col2:
            st.markdown("### 🏛️ Ontario Provincial Tax Brackets")
            ont_b_list = y_info.get("ontario_brackets", [])
            if ont_b_list:
                df_ont = pd.DataFrame([
                    {
                        "Upper Threshold": "No Upper Limit" if b["threshold"] >= 900000000 else f"${b['threshold']:,.2f}",
                        "Marginal Rate": f"{b['rate']*100:.2f}%"
                    }
                    for b in ont_b_list
                ])
                st.table(df_ont)

    # =========================================================================
    # TAB 3: JSON CONFIGURATION EDITOR
    # =========================================================================
    with tab_json:
        st.subheader("Single Source of Truth (`tax_thresholds.json`)")
        st.markdown("Edit your underlying JSON parameters below and save directly to disk.")
        raw_json_str = json.dumps(thresholds_db, indent=2)
        edited_json = st.text_area("JSON Configuration", value=raw_json_str, height=450)
        if st.button("💾 Save Configuration to tax_thresholds.json"):
            try:
                parsed = json.loads(edited_json)
                with open("tax_thresholds.json", "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2)
                st.success("Saved `tax_thresholds.json` successfully! Refresh or rerun to apply.")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON syntax: {e}")


if __name__ == "__main__":
    main()
