import json
import os
from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Canadian Public Service & Healthcare Retirement Calculator",
    page_icon="🍁",
    layout="wide",
    initial_sidebar_state="expanded",
)

THRESHOLD_FILE = "tax_thresholds.json"

DEFAULT_THRESHOLDS = {
    "2026": {
        "source": "CRA Indexation Bulletin & Ontario Ministry of Finance (2026)",
        "federal": {
            "brackets": [58523.0, 117045.0, 181440.0, 258482.0],
            "rates": [0.14, 0.205, 0.26, 0.29, 0.33],
            "bpa": 16452.0,
            "bpa_rate": 0.14,
        },
        "provincial": {
            "brackets": [53891.0, 107785.0, 150000.0, 220000.0],
            "rates": [0.0505, 0.0915, 0.1116, 0.1216, 0.1316],
            "bpa": 12989.0,
            "bpa_rate": 0.0505,
        },
    },
    "2025": {
        "source": "CRA Indexation Bulletin & Ontario Ministry of Finance (2025)",
        "federal": {
            "brackets": [57375.0, 114750.0, 177882.0, 253414.0],
            "rates": [0.15, 0.205, 0.26, 0.29, 0.33],
            "bpa": 15705.0,
            "bpa_rate": 0.15,
        },
        "provincial": {
            "brackets": [52886.0, 105775.0, 150000.0, 220000.0],
            "rates": [0.0505, 0.0915, 0.1116, 0.1216, 0.1316],
            "bpa": 12399.0,
            "bpa_rate": 0.0505,
        },
    },
}


def load_tax_thresholds() -> Dict[str, Any]:
    if "thresholds_db" in st.session_state:
        return st.session_state["thresholds_db"]
    if os.path.exists(THRESHOLD_FILE):
        try:
            with open(THRESHOLD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state["thresholds_db"] = data
                return data
        except Exception:
            pass
    st.session_state["thresholds_db"] = json.loads(json.dumps(DEFAULT_THRESHOLDS))
    return st.session_state["thresholds_db"]


@dataclass
class ScenarioInput:
    name: str
    category: str
    employment_income: float = 0.0
    pension_income: float = 0.0
    cpp_income: float = 0.0
    oas_income: float = 0.0
    rrsp_withdrawal: float = 0.0
    age: int = 64
    is_working: bool = True
    tax_year: str = "2026"
    t4_box14_employment: float = 0.0
    t4_box16_cpp1: float = 0.0
    t4_box16_cpp2: float = 0.0
    t4_box18_ei: float = 0.0
    t4_box20_rpp: float = 0.0
    t4_box22_tax_deducted: float = 0.0
    t4_box44_union: float = 0.0
    t4_box52_pa: float = 0.0
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
    fed_steps: List[str] = None
    prov_steps: List[str] = None
    credit_steps: List[str] = None


def calculate_ontario_tax_and_net(s: ScenarioInput, thresholds_db: Dict[str, Any]) -> TaxAndNetResult:
    year_key = s.tax_year if s.tax_year in thresholds_db else "2026"
    y_data = thresholds_db[year_key]

    gross = (
        s.employment_income
        + s.pension_income
        + s.cpp_income
        + s.oas_income
        + s.rrsp_withdrawal
    )

    if s.is_working and s.employment_income > 0:
        pssa = s.t4_box20_rpp if s.t4_box20_rpp > 0 else (s.employment_income * 0.06002)
        union = s.t4_box44_union if s.t4_box44_union > 0 else (s.employment_income * 0.01627)
        ei = s.t4_box18_ei if s.t4_box18_ei > 0 else (min(s.employment_income, 68900.0) * 0.0163)
        cpp1 = s.t4_box16_cpp1 if s.t4_box16_cpp1 > 0 else (
            max(0.0, min(s.employment_income, 74600.0) - 3500.0) * 0.0595
        )
        cpp2 = s.t4_box16_cpp2 if s.t4_box16_cpp2 > 0 else (
            max(0.0, min(s.employment_income, 85000.0) - 74600.0) * 0.04
        )
        cpp = cpp1 + cpp2
    else:
        pssa = 0.0
        union = 0.0
        ei = 0.0
        cpp1 = 0.0
        cpp2 = 0.0
        cpp = 0.0

    taxable_income = max(0.0, gross - pssa - union)

    # Federal Gross Tax
    fed_conf = y_data["federal"]
    fed_brackets = fed_conf["brackets"]
    fed_rates = fed_conf["rates"]

    fed_steps = []
    fed_gross = 0.0
    prev_b = 0.0
    for idx, b in enumerate(fed_brackets):
        rate = fed_rates[idx]
        if taxable_income <= b:
            rem = taxable_income - prev_b
            part = rem * rate
            fed_gross += part
            fed_steps.append(f"Tier {idx+1} (${prev_b:,.0f} – ${b:,.0f} @ {rate*100:.1f}%): ${rem:,.2f} × {rate*100:.1f}% = ${part:,.2f}")
            prev_b = -1
            break
        else:
            rem = b - prev_b
            part = rem * rate
            fed_gross += part
            fed_steps.append(f"Tier {idx+1} (${prev_b:,.0f} – ${b:,.0f} @ {rate*100:.1f}%): ${rem:,.2f} × {rate*100:.1f}% = ${part:,.2f}")
            prev_b = b

    if prev_b != -1:
        rate = fed_rates[-1]
        rem = taxable_income - fed_brackets[-1]
        part = rem * rate
        fed_gross += part
        fed_steps.append(f"Top Tier (Over ${fed_brackets[-1]:,.0f} @ {rate*100:.1f}%): ${rem:,.2f} × {rate*100:.1f}% = ${part:,.2f}")

    # Provincial Gross Tax
    prov_conf = y_data["provincial"]
    prov_brackets = prov_conf["brackets"]
    prov_rates = prov_conf["rates"]

    prov_steps = []
    prov_gross = 0.0
    prev_pb = 0.0
    for idx, pb in enumerate(prov_brackets):
        rate = prov_rates[idx]
        if taxable_income <= pb:
            rem = taxable_income - prev_pb
            part = rem * rate
            prov_gross += part
            prov_steps.append(f"Tier {idx+1} (${prev_pb:,.0f} – ${pb:,.0f} @ {rate*100:.2f}%): ${rem:,.2f} × {rate*100:.2f}% = ${part:,.2f}")
            prev_pb = -1
            break
        else:
            rem = pb - prev_pb
            part = rem * rate
            prov_gross += part
            prov_steps.append(f"Tier {idx+1} (${prev_pb:,.0f} – ${pb:,.0f} @ {rate*100:.2f}%): ${rem:,.2f} × {rate*100:.2f}% = ${part:,.2f}")
            prev_pb = pb

    if prev_pb != -1:
        rate = prov_rates[-1]
        rem = taxable_income - prov_brackets[-1]
        part = rem * rate
        prov_gross += part
        prov_steps.append(f"Top Tier (Over ${prov_brackets[-1]:,.0f} @ {rate*100:.2f}%): ${rem:,.2f} × {rate*100:.2f}% = ${part:,.2f}")

    # Credits
    credit_steps = []
    fed_bpa_amt = fed_conf.get("bpa", 16452.0)
    fed_bpa_rate = fed_conf.get("bpa_rate", 0.14)
    prov_bpa_amt = prov_conf.get("bpa", 12989.0)
    prov_bpa_rate = prov_conf.get("bpa_rate", 0.0505)

    fed_bpa_credit = fed_bpa_amt * fed_bpa_rate
    prov_bpa_credit = prov_bpa_amt * prov_bpa_rate
    credit_steps.append(f"Federal BPA (${fed_bpa_amt:,.0f} @ {fed_bpa_rate*100:.1f}%): -${fed_bpa_credit:,.2f}")
    credit_steps.append(f"Ontario BPA (${prov_bpa_amt:,.0f} @ {prov_bpa_rate*100:.2f}%): -${prov_bpa_credit:,.2f}")

    fed_emp_credit = 0.0
    if s.employment_income > 0:
        fed_emp_credit = min(s.employment_income, 1471.0) * fed_bpa_rate
        credit_steps.append(f"Canada Employment Amount Credit: -${fed_emp_credit:,.2f}")

    fed_cpp_ei_credit = (cpp + ei) * fed_bpa_rate
    prov_cpp_ei_credit = (cpp + ei) * prov_bpa_rate
    if (cpp + ei) > 0:
        credit_steps.append(f"CPP1 (${cpp1:,.2f}) + CPP2 (${cpp2:,.2f}) + EI (${ei:,.2f}) Credits (Fed + Prov): -${(fed_cpp_ei_credit + prov_cpp_ei_credit):,.2f}")

    eligible_pension = s.pension_income
    fed_pension_credit = min(eligible_pension, 2000.0) * fed_bpa_rate
    prov_pension_credit = min(eligible_pension, 1714.0) * prov_bpa_rate
    if eligible_pension > 0:
        credit_steps.append(f"Pension Income Tax Credit (Fed + Prov): -${(fed_pension_credit + prov_pension_credit):,.2f}")

    fed_age_credit = 0.0
    prov_age_credit = 0.0
    fed_age_clawback = 0.0
    if s.age >= 65:
        fed_age_base = 9208.0
        fed_age_clawback = max(0.0, (taxable_income - 45522.0) * 0.15)
        fed_age_credit = max(0.0, fed_age_base - fed_age_clawback) * fed_bpa_rate

        prov_age_base = 6351.0
        prov_age_clawback = max(0.0, (taxable_income - 46330.0) * 0.15)
        prov_age_credit = max(0.0, prov_age_base - prov_age_clawback) * prov_bpa_rate
        credit_steps.append(f"Age 65+ Tax Credits (Fed + Prov, net of clawbacks): -${(fed_age_credit + prov_age_credit):,.2f}")

    total_fed_credits = fed_bpa_credit + fed_emp_credit + fed_cpp_ei_credit + fed_pension_credit + fed_age_credit
    total_prov_credits = prov_bpa_credit + prov_cpp_ei_credit + prov_pension_credit + prov_age_credit

    fed_net = max(0.0, fed_gross - total_fed_credits)
    prov_basic_net = max(0.0, prov_gross - total_prov_credits)

    surtax = 0.0
    if prov_basic_net > 5818.0:
        surtax += (prov_basic_net - 5818.0) * 0.20
    if prov_basic_net > 7446.0:
        surtax += (prov_basic_net - 7446.0) * 0.36

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
    calc_total_tax = fed_net + prov_net

    if s.t4_box22_tax_deducted > 0:
        total_tax = s.t4_box22_tax_deducted
        fed_net = total_tax * 0.65
        prov_net = total_tax * 0.35
    else:
        total_tax = calc_total_tax

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

    total_deductions = pssa + union + cpp + ei + total_tax + other_deductions
    annual_net = gross - total_deductions
    eff_rate = (total_tax / gross * 100.0) if gross > 0 else 0.0

    return TaxAndNetResult(
        name=s.name,
        tax_year=year_key,
        gross_income=gross,
        pssa_deduction=pssa,
        union_dues=union,
        cpp1_deduction=cpp1,
        cpp2_deduction=cpp2,
        cpp_deduction=cpp,
        ei_deduction=ei,
        taxable_income=taxable_income,
        fed_tax_gross=fed_gross,
        prov_tax_gross=prov_gross,
        fed_bpa_credit_amt=fed_bpa_credit,
        prov_bpa_credit_amt=prov_bpa_credit,
        fed_pension_credit_amt=fed_pension_credit,
        prov_pension_credit_amt=prov_pension_credit,
        fed_age_credit_amt=fed_age_credit,
        prov_age_credit_amt=prov_age_credit,
        fed_age_clawback_amt=fed_age_clawback,
        total_fed_credits=total_fed_credits,
        total_prov_credits=total_prov_credits,
        total_credits_savings=total_fed_credits + total_prov_credits,
        fed_tax_net=fed_net,
        prov_basic_net=prov_basic_net,
        ontario_surtax=surtax,
        health_premium=ohp,
        prov_tax_net=prov_net,
        total_tax=total_tax,
        other_deductions=other_deductions,
        total_deductions=total_deductions,
        annual_net_cash=annual_net,
        biweekly_net_cash=annual_net / 26.0,
        monthly_net_cash=annual_net / 12.0,
        effective_tax_rate=eff_rate,
        fed_steps=fed_steps,
        prov_steps=prov_steps,
        credit_steps=credit_steps,
    )


def get_paula_presets(tax_year: str = "2026") -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="Last Year (Full-Time)",
            category="Paula",
            employment_income=91610.75,
            age=63,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=91610.75,
            t4_box20_rpp=5498.83,
            t4_box22_tax_deducted=16009.57,
            t4_box44_union=1490.28,
            exp_parking=1200.0,
            exp_lunch=1500.0,
        ),
        ScenarioInput(
            name="Continue Work (4-Day + CPP)",
            category="Paula",
            employment_income=69006.00,
            cpp_income=17280.00,
            age=64,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=69006.00,
            t4_box20_rpp=69006.00 * (5498.83 / 91610.75),
            t4_box44_union=69006.00 * (1490.28 / 91610.75),
            exp_parking=960.0,
            exp_lunch=1200.0,
        ),
        ScenarioInput(
            name="Retire @ 64 (Pension + CPP)",
            category="Paula",
            pension_income=37200.00,
            cpp_income=17280.00,
            age=64,
            is_working=False,
            tax_year=tax_year,
        ),
        ScenarioInput(
            name="Retire @ 64 + $15k RRSP",
            category="Paula",
            pension_income=37200.00,
            cpp_income=17280.00,
            rrsp_withdrawal=15000.00,
            age=64,
            is_working=False,
            tax_year=tax_year,
        ),
        ScenarioInput(
            name="Retire 2027 @ 65 (+ OAS)",
            category="Paula",
            pension_income=37944.00,
            cpp_income=17625.00,
            oas_income=7334.64,
            age=65,
            is_working=False,
            tax_year=tax_year,
        ),
    ]


def get_randy_presets(tax_year: str = "2026") -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="Future (IT-03 + CPP)",
            category="Randy",
            employment_income=126114.89,
            cpp_income=18091.80,
            age=65,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=126114.89,
            t4_box20_rpp=12777.49,
            t4_box44_union=1080.72,
            work_expenses=9216.00,
            exp_fuel=2400.0,
            exp_parking=1800.0,
        ),
        ScenarioInput(
            name="Current (IT-03 Full-Time)",
            category="Randy",
            employment_income=126114.89,
            age=64,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=126114.89,
            t4_box20_rpp=12777.49,
            t4_box44_union=1080.72,
            work_expenses=9216.00,
            exp_fuel=2400.0,
            exp_parking=1800.0,
        ),
        ScenarioInput(
            name="PRTL (4-Day + CPP)",
            category="Randy",
            employment_income=100891.91,
            cpp_income=18091.80,
            age=65,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=100891.91,
            t4_box20_rpp=12777.49 * (100891.91 / 126114.89),
            t4_box44_union=1080.72 * (100891.91 / 126114.89),
            work_expenses=9216.00,
            exp_fuel=1920.0,
            exp_parking=1440.0,
        ),
        ScenarioInput(
            name="PRTL (3-Day + CPP/OAS)",
            category="Randy",
            employment_income=75668.93,
            cpp_income=18091.80,
            oas_income=9023.64,
            age=65,
            is_working=True,
            tax_year=tax_year,
            t4_box14_employment=75668.93,
            t4_box20_rpp=12777.49 * (75668.93 / 126114.89),
            t4_box44_union=1080.72 * (75668.93 / 126114.89),
            work_expenses=9216.00,
            exp_fuel=1440.0,
            exp_parking=1080.0,
        ),
        ScenarioInput(
            name="Retirement Nov @ 65",
            category="Randy",
            pension_income=53607.96,
            cpp_income=18091.80,
            oas_income=9023.64,
            rrsp_withdrawal=521.00,
            age=65,
            is_working=False,
            tax_year=tax_year,
            health_dental_benefits=3100.56,
        ),
    ]


def build_comparison_dataframe(results: List[TaxAndNetResult]) -> pd.DataFrame:
    metrics = [
        ("Tax Year Threshold Engine", [r.tax_year for r in results]),
        ("Annual Gross Income", [f"${r.gross_income:,.2f}" for r in results]),
        ("PSSA Pension Contribution (Box 20 RPP)", [f"-${r.pssa_deduction:,.2f}" for r in results]),
        ("Union Dues (Box 44)", [f"-${r.union_dues:,.2f}" for r in results]),
        ("CPP1 Contributions - Base (Box 16)", [f"-${r.cpp1_deduction:,.2f}" for r in results]),
        ("CPP2 Contributions - Additional (Box 16A)", [f"-${r.cpp2_deduction:,.2f}" for r in results]),
        ("EI Premiums (Box 18)", [f"-${r.ei_deduction:,.2f}" for r in results]),
        ("Federal BPA Credit", [f"-${r.fed_bpa_credit_amt:,.2f}" for r in results]),
        ("Ontario BPA Credit", [f"-${r.prov_bpa_credit_amt:,.2f}" for r in results]),
        ("Federal Pension Credit", [f"-${r.fed_pension_credit_amt:,.2f}" for r in results]),
        ("Ontario Pension Credit", [f"-${r.prov_pension_credit_amt:,.2f}" for r in results]),
        ("Federal Age Credit (Net of Clawback)", [f"-${r.fed_age_credit_amt:,.2f}" for r in results]),
        ("Ontario Age Credit", [f"-${r.prov_age_credit_amt:,.2f}" for r in results]),
        ("Federal Age Credit Clawback", [f"${r.fed_age_clawback_amt:,.2f}" for r in results]),
        ("Total Tax Savings from Credits", [f"-${r.total_credits_savings:,.2f}" for r in results]),
        ("Federal Income Tax (Net)", [f"${r.fed_tax_net:,.2f}" for r in results]),
        ("Provincial Income Tax (Basic Net)", [f"${r.prov_basic_net:,.2f}" for r in results]),
        ("Ontario Surtax", [f"${r.ontario_surtax:,.2f}" for r in results]),
        ("Ontario Health Premium (OHP)", [f"${r.health_premium:,.2f}" for r in results]),
        ("Provincial Tax (Total incl. Surtax & OHP)", [f"${r.prov_tax_net:,.2f}" for r in results]),
        ("TOTAL ANNUAL TAX PAID", [f"-${r.total_tax:,.2f}" for r in results]),
        ("Effective Tax Rate (%)", [f"{r.effective_tax_rate:.2f}%" for r in results]),
        ("Other Expenses (Bus/Lunch/Fuel/Lottery)", [f"-${r.other_deductions:,.2f}" for r in results]),
        ("TOTAL ANNUAL DEDUCTIONS & EXPENSES", [f"-${r.total_deductions:,.2f}" for r in results]),
        ("ANNUAL NET TAKE-HOME PAY", [f"${r.annual_net_cash:,.2f}" for r in results]),
        ("MONTHLY NET CASH FLOW", [f"${r.monthly_net_cash:,.2f}" for r in results]),
        ("BI-WEEKLY NET PAYCHEQUE", [f"${r.biweekly_net_cash:,.2f}" for r in results]),
    ]

    data = {"Financial / Tax Line Item": [m[0] for m in metrics]}
    for idx, res in enumerate(results):
        col_name = res.name if res.name not in data else f"{res.name} ({idx+1})"
        data[col_name] = [m[1][idx] for m in metrics]

    return pd.DataFrame(data)


def render_step_by_step_breakdown(res: TaxAndNetResult):
    with st.expander(f"🧮 Step-by-Step Tax Calculation Breakdown: {res.name} ({res.tax_year})", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 1. Gross to Taxable Income")
            st.write(f"- **Annual Gross Income:** `${res.gross_income:,.2f}`")
            st.write(f"- **Less PSSA Pension (Box 20):** `-${res.pssa_deduction:,.2f}`")
            st.write(f"- **Less Union Dues (Box 44):** `-${res.union_dues:,.2f}`")
            st.info(f"**Final Taxable Income:** `${res.taxable_income:,.2f}`")

            st.markdown(f"#### 2. Federal Gross Tax ({res.tax_year} Brackets)")
            for step in res.fed_steps:
                st.write(f"- {step}")
            st.write(f"**Total Federal Gross Tax:** `${res.fed_tax_gross:,.2f}`")

        with c2:
            st.markdown(f"#### 3. Ontario Provincial Gross Tax ({res.tax_year} Brackets)")
            for step in res.prov_steps:
                st.write(f"- {step}")
            st.write(f"**Total Provincial Gross Tax:** `${res.prov_tax_gross:,.2f}`")

            st.markdown("#### 4. Non-Refundable Tax Credits & Surtaxes")
            for step in res.credit_steps:
                st.write(f"- {step}")
            st.write(f"- **Total Credit Savings:** `-${res.total_credits_savings:,.2f}`")
            st.write(f"- **Ontario Surtax:** `${res.ontario_surtax:,.2f}`")
            st.write(f"- **Ontario Health Premium (OHP):** `${res.health_premium:,.2f}`")
            st.error(f"**TOTAL NET TAX PAYABLE:** `${res.total_tax:,.2f}` ({res.effective_tax_rate:.1f}% Effective Rate)")


def main():
    thresholds_db = load_tax_thresholds()
    available_years = sorted(list(thresholds_db.keys()), reverse=True)

    st.title("🍁 Canadian Public Service & Healthcare Retirement Calculator")
    st.caption(
        "Interactive Retirement Cash Flow, T4 Deduction, and Ontario Tax Simulation Tool. "
        "*Disclaimer: For educational and estimation purposes only; does not constitute formal financial, tax, or pension advice.*"
    )

    if "pinned_scenarios" not in st.session_state:
        st.session_state["pinned_scenarios"] = []

    tab_paula, tab_randy, tab_sandbox, tab_thresholds = st.tabs([
        "👩‍⚕️ Paula's Scenarios",
        "👨‍💻 Randy's Scenarios",
        "🎛️ Interactive Scenario Sandbox (T4 Entry)",
        "⚙️ Tax Thresholds & Indexation Viewer",
    ])

    # --- TAB 1: PAULA ---
    with tab_paula:
        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.subheader("Paula's Hospital Shift & Retirement Scenarios")
        with col_top2:
            paula_year = st.selectbox("Tax Year Engine (Paula)", available_years, index=0, key="paula_yr")

        paula_results = [calculate_ontario_tax_and_net(s, thresholds_db) for s in get_paula_presets(paula_year)]

        kpi_cols = st.columns(len(paula_results))
        for idx, res in enumerate(paula_results):
            with kpi_cols[idx]:
                st.metric(
                    label=res.name,
                    value=f"${res.annual_net_cash:,.0f}/yr",
                    delta=f"${res.monthly_net_cash:,.0f}/mo ({res.effective_tax_rate:.1f}% tax)",
                )

        df_paula = build_comparison_dataframe(paula_results)
        st.dataframe(df_paula, use_container_width=True, hide_index=True, height=620)

        col_dl, col_sel = st.columns([1, 2])
        with col_dl:
            st.download_button(
                label="📥 Download Paula's Table (CSV)",
                data=df_paula.to_csv(index=False).encode("utf-8"),
                file_name=f"paula_retirement_scenarios_{paula_year}.csv",
                mime="text/csv",
            )
        with col_sel:
            sel_paula = st.selectbox("Inspect Detailed Tax Breakdown for:", [r.name for r in paula_results], key="sel_p_bd")
        target_p = next(r for r in paula_results if r.name == sel_paula)
        render_step_by_step_breakdown(target_p)

    # --- TAB 2: RANDY ---
    with tab_randy:
        col_r1, col_r2 = st.columns([3, 1])
        with col_r1:
            st.subheader("Randy's GoC IT-03, PRTL & November Retirement Scenarios")
        with col_r2:
            randy_year = st.selectbox("Tax Year Engine (Randy)", available_years, index=0, key="randy_yr")

        randy_results = [calculate_ontario_tax_and_net(s, thresholds_db) for s in get_randy_presets(randy_year)]

        kpi_cols_r = st.columns(len(randy_results))
        for idx, res in enumerate(randy_results):
            with kpi_cols_r[idx]:
                st.metric(
                    label=res.name,
                    value=f"${res.annual_net_cash:,.0f}/yr",
                    delta=f"${res.monthly_net_cash:,.0f}/mo ({res.effective_tax_rate:.1f}% tax)",
                )

        df_randy = build_comparison_dataframe(randy_results)
        st.dataframe(df_randy, use_container_width=True, hide_index=True, height=620)

        col_dl_r, col_sel_r = st.columns([1, 2])
        with col_dl_r:
            st.download_button(
                label="📥 Download Randy's Table (CSV)",
                data=df_randy.to_csv(index=False).encode("utf-8"),
                file_name=f"randy_retirement_scenarios_{randy_year}.csv",
                mime="text/csv",
            )
        with col_sel_r:
            sel_randy = st.selectbox("Inspect Detailed Tax Breakdown for:", [r.name for r in randy_results], key="sel_r_bd")
        target_r = next(r for r in randy_results if r.name == sel_randy)
        render_step_by_step_breakdown(target_r)

    # --- TAB 3: SANDBOX ---
    with tab_sandbox:
        st.subheader("🎛️ Interactive Scenario Sandbox (Custom T4 Slip & Retirement Entry)")
        sb_left, sb_right = st.columns([1, 2], gap="large")

        with sb_left:
            st.markdown("#### Configure Scenario Inputs")
            template = st.selectbox(
                "Quick-Load Baseline Template:",
                [
                    "Custom / Current Values",
                    "Paula Preset (4-Day Shift + CPP)",
                    "Paula Preset (Retire @ 64 + $15k RRSP)",
                    "Randy Preset (PRTL 4-Day + CPP)",
                    "Randy Preset (Full Retire @ 65)",
                ],
            )

            # Default values based on template selection
            def_name = "Custom Scenario A"
            def_age = 64
            def_working = True
            def_box14 = 91610.75
            def_cpp1 = 4230.45
            def_cpp2 = 416.00
            def_ei = 1050.00
            def_box20 = 5498.83
            def_box22 = 16009.57
            def_box44 = 1490.28
            def_pension = 0.0
            def_cpp_ret = 17280.0
            def_oas = 0.0
            def_rrsp = 0.0
            def_lunch = 1500.0
            def_parking = 1200.0
            def_fuel = 0.0

            if template == "Paula Preset (4-Day Shift + CPP)":
                def_name = "Paula 4-Day + CPP"
                def_box14 = 69006.00
                def_cpp1 = 3897.60
                def_cpp2 = 0.0
                def_ei = 950.0
                def_box20 = 69006.00 * (5498.83 / 91610.75)
                def_box22 = 10159.86
                def_box44 = 69006.00 * (1490.28 / 91610.75)
                def_lunch = 1200.0
                def_parking = 960.0
            elif template == "Paula Preset (Retire @ 64 + $15k RRSP)":
                def_name = "Paula Retire + $15k RRSP"
                def_working = False
                def_box14 = 0.0
                def_box22 = 0.0
                def_pension = 37200.0
                def_rrsp = 15000.0
                def_lunch = 0.0
                def_parking = 0.0
            elif template == "Randy Preset (PRTL 4-Day + CPP)":
                def_name = "Randy PRTL 4-Day"
                def_age = 65
                def_box14 = 100891.91
                def_box20 = 12777.49 * (100891.91 / 126114.89)
                def_box22 = 19500.0
                def_box44 = 1080.72 * (100891.91 / 126114.89)
                def_cpp_ret = 18091.80
                def_lunch = 0.0
                def_parking = 1440.0
                def_fuel = 1920.0
            elif template == "Randy Preset (Full Retire @ 65)":
                def_name = "Randy Retire @ 65"
                def_age = 65
                def_working = False
                def_box14 = 0.0
                def_box22 = 0.0
                def_pension = 53607.96
                def_cpp_ret = 18091.80
                def_oas = 9023.64
                def_rrsp = 521.0
                def_lunch = 0.0
                def_parking = 0.0

            sc_name = st.text_input("Scenario Label", value=def_name)
            sc_year = st.selectbox("Tax Year Threshold Engine", available_years, index=0)
            sc_age = st.number_input("Age in Tax Year (65+ triggers Age Credits)", min_value=50, max_value=95, value=def_age)
            sc_working = st.checkbox("Currently Working (Include T4 Employment & CPP/EI)", value=def_working)

            with st.expander("🧾 T4 Slip Employment & Deduction Boxes", expanded=sc_working):
                t4_14 = st.number_input("T4 Box 14 - Employment Income ($)", min_value=0.0, value=float(def_box14), step=500.0)
                t4_16_1 = st.number_input("T4 Box 16 - CPP1 Base ($)", min_value=0.0, value=float(def_cpp1), step=100.0)
                t4_16_2 = st.number_input("T4 Box 16A - CPP2 Additional ($)", min_value=0.0, value=float(def_cpp2), step=50.0)
                t4_18 = st.number_input("T4 Box 18 - EI Premiums ($)", min_value=0.0, value=float(def_ei), step=50.0)
                t4_20 = st.number_input("T4 Box 20 - RPP / PSSA Contributions ($)", min_value=0.0, value=float(def_box20), step=200.0)
                t4_22 = st.number_input("T4 Box 22 - Tax Deducted Override (0 = Auto)", min_value=0.0, value=float(def_box22), step=500.0)
                t4_44 = st.number_input("T4 Box 44 - Union Dues ($)", min_value=0.0, value=float(def_box44), step=100.0)

            with st.expander("🏦 Retirement Income Sources", expanded=True):
                inc_pension = st.number_input("Defined Benefit Pension Income ($)", min_value=0.0, value=float(def_pension), step=500.0)
                inc_cpp = st.number_input("CPP Retirement Benefits ($)", min_value=0.0, value=float(def_cpp_ret), step=500.0)
                inc_oas = st.number_input("OAS Retirement Benefits ($)", min_value=0.0, value=float(def_oas), step=250.0)
                inc_rrsp = st.number_input("RRSP / RRIF Withdrawal ($)", min_value=0.0, value=float(def_rrsp), step=1000.0)

            with st.expander("💸 Out-of-Pocket & Work Expenses", expanded=False):
                exp_bus = st.number_input("Bus Fare / Transit ($)", min_value=0.0, value=0.0, step=100.0)
                exp_lunch = st.number_input("Lunch / Work Meals ($)", min_value=0.0, value=float(def_lunch), step=100.0)
                exp_parking = st.number_input("Parking Fee ($)", min_value=0.0, value=float(def_parking), step=100.0)
                exp_fuel = st.number_input("Vehicle Fuel ($)", min_value=0.0, value=float(def_fuel), step=100.0)
                exp_lottery = st.number_input("Lottery / Discretionary ($)", min_value=0.0, value=0.0, step=100.0)
                exp_other = st.number_input("Other General Expenses ($)", min_value=0.0, value=0.0, step=100.0)

            active_input = ScenarioInput(
                name=sc_name or "Custom Scenario",
                category="Custom",
                employment_income=t4_14 if sc_working else 0.0,
                pension_income=inc_pension,
                cpp_income=inc_cpp,
                oas_income=inc_oas,
                rrsp_withdrawal=inc_rrsp,
                age=int(sc_age),
                is_working=sc_working,
                tax_year=sc_year,
                t4_box14_employment=t4_14,
                t4_box16_cpp1=t4_16_1,
                t4_box16_cpp2=t4_16_2,
                t4_box18_ei=t4_18,
                t4_box20_rpp=t4_20,
                t4_box22_tax_deducted=t4_22 if sc_working else 0.0,
                t4_box44_union=t4_44,
                exp_bus=exp_bus,
                exp_lunch=exp_lunch,
                exp_parking=exp_parking,
                exp_fuel=exp_fuel,
                exp_lottery=exp_lottery,
                exp_other=exp_other,
            )

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("📌 Pin Scenario to Compare", use_container_width=True):
                    if len(st.session_state["pinned_scenarios"]) >= 3:
                        st.warning("Maximum 3 pinned scenarios allowed.")
                    else:
                        st.session_state["pinned_scenarios"].append(active_input)
            with btn_c2:
                if st.button("🗑️ Clear Pinned", use_container_width=True):
                    st.session_state["pinned_scenarios"] = []

        with sb_right:
            active_res = calculate_ontario_tax_and_net(active_input, thresholds_db)
            all_sb_results = [active_res] + [
                calculate_ontario_tax_and_net(p, thresholds_db) for p in st.session_state["pinned_scenarios"]
            ]

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Annual Gross", f"${active_res.gross_income:,.2f}")
            k2.metric(f"Total Tax ({active_res.tax_year})", f"-${active_res.total_tax:,.2f}", f"{active_res.effective_tax_rate:.1f}% eff.")
            k3.metric("Annual Net Cash", f"${active_res.annual_net_cash:,.2f}")
            k4.metric("Monthly Net Cash", f"${active_res.monthly_net_cash:,.2f}", f"${active_res.biweekly_net_cash:,.2f}/bi-wk")

            df_sb = build_comparison_dataframe(all_sb_results)
            st.dataframe(df_sb, use_container_width=True, hide_index=True, height=620)

            st.download_button(
                label="📥 Export Sandbox Comparison (CSV)",
                data=df_sb.to_csv(index=False).encode("utf-8"),
                file_name="custom_retirement_comparison.csv",
                mime="text/csv",
            )
            render_step_by_step_breakdown(active_res)

    # --- TAB 4: TAX THRESHOLDS MANAGER ---
    with tab_thresholds:
        st.subheader("📑 Government Tax Thresholds & Indexation Viewer")
        inspected_year = st.selectbox("Select Tax Year to View:", available_years, index=0, key="view_th_yr")
        y_info = thresholds_db[inspected_year]

        st.info(f"**Published Source:** {y_info.get('source', 'Official CRA & Provincial Indexation')}")

        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown(f"#### 🇨🇦 Federal Tax Brackets & BPA ({inspected_year})")
            fed_c = y_info["federal"]
            st.write(f"- **Basic Personal Amount (BPA):** `${fed_c['bpa']:,.2f}` (Credit Rate: `{fed_c['bpa_rate']*100:.1f}%`)")
            fed_rows = []
            prev = 0.0
            for idx, b in enumerate(fed_c["brackets"]):
                fed_rows.append({"Tier": f"Tier {idx+1}", "Income Range": f"${prev:,.0f} – ${b:,.0f}", "Marginal Rate": f"{fed_c['rates'][idx]*100:.1f}%"})
                prev = b
            fed_rows.append({"Tier": "Top Tier", "Income Range": f"Over ${fed_c['brackets'][-1]:,.0f}", "Marginal Rate": f"{fed_c['rates'][-1]*100:.1f}%"})
            st.table(pd.DataFrame(fed_rows))

        with tc2:
            st.markdown(f"#### 🏛️ Ontario Provincial Tax Brackets & BPA ({inspected_year})")
            prov_c = y_info["provincial"]
            st.write(f"- **Ontario Basic Personal Amount (BPA):** `${prov_c['bpa']:,.2f}` (Credit Rate: `{prov_c['bpa_rate']*100:.2f}%`)")
            prov_rows = []
            prev_p = 0.0
            for idx, pb in enumerate(prov_c["brackets"]):
                prov_rows.append({"Tier": f"Tier {idx+1}", "Income Range": f"${prev_p:,.0f} – ${pb:,.0f}", "Marginal Rate": f"{prov_c['rates'][idx]*100:.2f}%"})
                prev_p = pb
            prov_rows.append({"Tier": "Top Tier", "Income Range": f"Over ${prov_c['brackets'][-1]:,.0f}", "Marginal Rate": f"{prov_c['rates'][-1]*100:.2f}%"})
            st.table(pd.DataFrame(prov_rows))

        with st.expander("📝 Advanced: Edit or Add New Tax Year JSON"):
            raw_json_input = st.text_area("Tax Thresholds JSON", value=json.dumps(thresholds_db, indent=4), height=320)
            if st.button("💾 Apply & Save Threshold Changes"):
                try:
                    updated_db = json.loads(raw_json_input)
                    st.session_state["thresholds_db"] = updated_db
                    with open(THRESHOLD_FILE, "w", encoding="utf-8") as f:
                        json.dump(updated_db, f, indent=4)
                    st.success("Tax thresholds updated! Refresh or switch tabs to see recalculated numbers.")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON syntax: {e}")


if __name__ == "__main__":
    main()
