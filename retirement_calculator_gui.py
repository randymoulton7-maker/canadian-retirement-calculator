#!/usr/bin/env python3
"""
Canadian Public Service & Healthcare Retirement Cash Flow Calculator - Desktop GUI (Tkinter)
Run in PowerShell: python retirement_calculator_gui.py
Zero external dependencies required (uses Python built-in tkinter & ttk).
"""

import csv
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from typing import List, Dict, Any

THRESHOLD_FILE = "tax_thresholds.json"

def load_tax_thresholds() -> Dict[str, Any]:
    default_data = {
        "2026": {
            "source": "CRA Indexation Bulletin & Ontario Ministry of Finance (2026)",
            "federal": {
                "brackets": [58523.0, 117045.0, 181440.0, 258482.0],
                "rates": [0.14, 0.205, 0.26, 0.29, 0.33],
                "bpa": 16452.0,
                "bpa_rate": 0.14
            },
            "provincial": {
                "brackets": [53891.0, 107785.0, 150000.0, 220000.0],
                "rates": [0.0505, 0.0915, 0.1116, 0.1216, 0.1316],
                "bpa": 12989.0,
                "bpa_rate": 0.0505
            }
        },
        "2025": {
            "source": "CRA Indexation Bulletin & Ontario Ministry of Finance (2025)",
            "federal": {
                "brackets": [57375.0, 114750.0, 177882.0, 253414.0],
                "rates": [0.15, 0.205, 0.26, 0.29, 0.33],
                "bpa": 15705.0,
                "bpa_rate": 0.15
            },
            "provincial": {
                "brackets": [52886.0, 105775.0, 150000.0, 220000.0],
                "rates": [0.0505, 0.0915, 0.1116, 0.1216, 0.1316],
                "bpa": 12399.0,
                "bpa_rate": 0.0505
            }
        }
    }
    if os.path.exists(THRESHOLD_FILE):
        try:
            with open(THRESHOLD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_data
    else:
        with open(THRESHOLD_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        return default_data


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


def calculate_ontario_tax_and_net(s: ScenarioInput) -> TaxAndNetResult:
    thresholds_db = load_tax_thresholds()
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
            fed_steps.append(f"• Tier {idx+1} (${prev_b:,.0f} - ${b:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")
            prev_b = -1
            break
        else:
            rem = b - prev_b
            part = rem * rate
            fed_gross += part
            fed_steps.append(f"• Tier {idx+1} (${prev_b:,.0f} - ${b:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")
            prev_b = b

    if prev_b != -1:
        idx = len(fed_brackets)
        rate = fed_rates[-1]
        rem = taxable_income - fed_brackets[-1]
        part = rem * rate
        fed_gross += part
        fed_steps.append(f"• Top Tier (Over ${fed_brackets[-1]:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")

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
            prov_steps.append(f"• Tier {idx+1} (${prev_pb:,.0f} - ${pb:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")
            prev_pb = -1
            break
        else:
            rem = pb - prev_pb
            part = rem * rate
            prov_gross += part
            prov_steps.append(f"• Tier {idx+1} (${prev_pb:,.0f} - ${pb:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")
            prev_pb = pb

    if prev_pb != -1:
        idx = len(prov_brackets)
        rate = prov_rates[-1]
        rem = taxable_income - prov_brackets[-1]
        part = rem * rate
        prov_gross += part
        prov_steps.append(f"• Top Tier (Over ${prov_brackets[-1]:,.0f} @ {rate*100}%): ${rem:,.2f} × {rate*100}% = ${part:,.2f}")

    credit_steps = []
    fed_bpa_amt = fed_conf.get("bpa", 16452.0)
    fed_bpa_rate = fed_conf.get("bpa_rate", 0.14)
    prov_bpa_amt = prov_conf.get("bpa", 12989.0)
    prov_bpa_rate = prov_conf.get("bpa_rate", 0.0505)

    fed_bpa_credit = fed_bpa_amt * fed_bpa_rate
    prov_bpa_credit = prov_bpa_amt * prov_bpa_rate
    credit_steps.append(f"• Federal Basic Personal Amount (${fed_bpa_amt:,.0f} @ {fed_bpa_rate*100}%): -${fed_bpa_credit:,.2f}")
    credit_steps.append(f"• Ontario Basic Personal Amount (${prov_bpa_amt:,.0f} @ {prov_bpa_rate*100}%): -${prov_bpa_credit:,.2f}")

    fed_emp_credit = 0.0
    if s.employment_income > 0:
        fed_emp_credit = min(s.employment_income, 1471.0) * fed_bpa_rate
        credit_steps.append(f"• Canada Employment Amount Credit: -${fed_emp_credit:,.2f}")

    fed_cpp_ei_credit = (cpp + ei) * fed_bpa_rate
    prov_cpp_ei_credit = (cpp + ei) * prov_bpa_rate
    if (cpp + ei) > 0:
        credit_steps.append(f"• CPP1 (${cpp1:,.2f}) + CPP2 (${cpp2:,.2f}) + EI (${ei:,.2f}) Tax Credits (Fed + Prov): -${(fed_cpp_ei_credit + prov_cpp_ei_credit):,.2f}")

    eligible_pension = s.pension_income
    fed_pension_credit = min(eligible_pension, 2000.0) * fed_bpa_rate
    prov_pension_credit = min(eligible_pension, 1714.0) * prov_bpa_rate
    if eligible_pension > 0:
        credit_steps.append(f"• Pension Income Tax Credit (Fed + Prov): -${(fed_pension_credit + prov_pension_credit):,.2f}")

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
        credit_steps.append(f"• Age 65+ Amount Tax Credits (Fed + Prov, net of clawbacks): -${(fed_age_credit + prov_age_credit):,.2f}")

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


def get_paula_presets() -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="Last Year (Full-Time)",
            category="Paula",
            employment_income=91610.75,
            age=63,
            is_working=True,
            tax_year="2026",
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
            tax_year="2026",
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
            tax_year="2026",
        ),
        ScenarioInput(
            name="Retire @ 64 + $15k RRSP",
            category="Paula",
            pension_income=37200.00,
            cpp_income=17280.00,
            rrsp_withdrawal=15000.00,
            age=64,
            is_working=False,
            tax_year="2026",
        ),
        ScenarioInput(
            name="Retire 2027 @ 65 (+ OAS)",
            category="Paula",
            pension_income=37944.00,
            cpp_income=17625.00,
            oas_income=7334.64,
            age=65,
            is_working=False,
            tax_year="2026",
        ),
    ]


def get_randy_presets() -> List[ScenarioInput]:
    return [
        ScenarioInput(
            name="Future (IT-03 + CPP)",
            category="Randy",
            employment_income=126114.89,
            cpp_income=18091.80,
            age=65,
            is_working=True,
            tax_year="2026",
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
            tax_year="2026",
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
            tax_year="2026",
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
            tax_year="2026",
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
            tax_year="2026",
            health_dental_benefits=3100.56,
        ),
    ]


class TaxThresholdManagerWindow:
    def __init__(self, parent: tk.Tk, app_instance):
        self.parent = parent
        self.app_instance = app_instance
        self.top = tk.Toplevel(parent)
        self.top.title("⚙️ Tax Threshold Manager & Government Indexation Viewer")
        self.top.geometry("900x720")
        self.top.minsize(800, 600)
        self.top.configure(bg="#F0F4F8")

        header = tk.Frame(self.top, bg="#1E293B", height=64)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📑 Government Tax Thresholds & Indexation (Human-Readable View)",
            bg="#1E293B",
            fg="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
        ).pack(side=tk.LEFT, padx=20, pady=16)

        self.mgr_notebook = ttk.Notebook(self.top)
        self.mgr_notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        self.tab_readable = tk.Frame(self.mgr_notebook, bg="#F0F4F8")
        self.mgr_notebook.add(self.tab_readable, text="  📊 Human-Readable Summary  ")

        self.tab_json = tk.Frame(self.mgr_notebook, bg="#F0F4F8")
        self.mgr_notebook.add(self.tab_json, text="  📝 Advanced JSON Editor  ")

        self._build_readable_tab(self.tab_readable)
        self._build_json_tab(self.tab_json)

    def _build_readable_tab(self, parent):
        container = tk.Frame(parent, bg="#F0F4F8")
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        top_bar = tk.Frame(container, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        top_bar.pack(fill=tk.X, pady=(0, 10), ipady=8, ipadx=8)

        tk.Label(top_bar, text="Select Tax Year to Inspect:", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=8)
        
        self.thresholds_db = load_tax_thresholds()
        self.years_list = sorted(list(self.thresholds_db.keys()), reverse=True)
        self.selected_year_var = tk.StringVar(value=self.years_list[0] if self.years_list else "2026")

        year_combo = ttk.Combobox(top_bar, textvariable=self.selected_year_var, values=self.years_list, state="readonly", width=12, font=("Segoe UI", 10))
        year_combo.pack(side=tk.LEFT, padx=8)
        year_combo.bind("<<ComboboxSelected>>", self._refresh_readable_view)

        canvas = tk.Canvas(container, bg="#F0F4F8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.readable_scroll_frame = tk.Frame(canvas, bg="#F0F4F8")

        self.readable_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.readable_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_readable_view()

    def _refresh_readable_view(self, event=None):
        for widget in self.readable_scroll_frame.winfo_children():
            widget.destroy()

        year = self.selected_year_var.get()
        y_data = self.thresholds_db.get(year, {})
        source_desc = y_data.get("source", "Official CRA & Provincial Tax Indexation")

        src_card = tk.Frame(self.readable_scroll_frame, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        src_card.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=8)
        tk.Label(src_card, text=f"📌 Published Source for {year}:", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, padx=8, pady=(4, 2))
        tk.Label(src_card, text=source_desc, bg="#FFFFFF", fg="#334155", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=12, pady=(0, 4))

        fed_card = tk.Frame(self.readable_scroll_frame, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        fed_card.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=8)
        
        tk.Frame(fed_card, bg="#2563EB", height=4).pack(fill=tk.X)
        tk.Label(fed_card, text=f"🇨🇦 Federal Tax Brackets & Rates ({year})", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 6))

        fed_conf = y_data.get("federal", {})
        fed_brackets = fed_conf.get("brackets", [])
        fed_rates = fed_conf.get("rates", [])
        fed_bpa = fed_conf.get("bpa", 0.0)
        fed_bpa_rate = fed_conf.get("bpa_rate", 0.15)

        fed_lines = [
            f"• Basic Personal Amount (BPA): ${fed_bpa:,.2f} (Tax Credit Rate: {fed_bpa_rate*100:.1f}%)",
            "",
            "Tax Brackets & Marginal Rates:"
        ]
        
        prev = 0.0
        for i, b in enumerate(fed_brackets):
            rate = fed_rates[i] if i < len(fed_rates) else fed_rates[-1]
            fed_lines.append(f"  - Tier {i+1}: Taxable income from ${prev:,.2f} up to ${b:,.2f} is taxed at {rate*100:.1f}%")
            prev = b
        last_rate = fed_rates[-1] if fed_rates else 0.33
        fed_lines.append(f"  - Top Tier: Taxable income over ${fed_brackets[-1]:,.2f} is taxed at {last_rate*100:.1f}%")

        tk.Label(fed_card, text="\n".join(fed_lines), bg="#FFFFFF", fg="#334155", font=("Consolas", 9), justify=tk.LEFT).pack(anchor=tk.W, padx=12, pady=(0, 8))

        prov_card = tk.Frame(self.readable_scroll_frame, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        prov_card.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=8)
        
        tk.Frame(prov_card, bg="#4F46E5", height=4).pack(fill=tk.X)
        tk.Label(prov_card, text=f"🏛️ Ontario Provincial Tax Brackets & Rates ({year})", bg="#FFFFFF", fg="#0F172A", font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, padx=8, pady=(8, 6))

        prov_conf = y_data.get("provincial", {})
        prov_brackets = prov_conf.get("brackets", [])
        prov_rates = prov_conf.get("rates", [])
        prov_bpa = prov_conf.get("bpa", 0.0)
        prov_bpa_rate = prov_conf.get("bpa_rate", 0.0505)

        prov_lines = [
            f"• Ontario Basic Personal Amount (BPA): ${prov_bpa:,.2f} (Tax Credit Rate: {prov_bpa_rate*100:.2f}%)",
            "",
            "Tax Brackets & Marginal Rates:"
        ]
        
        prev_p = 0.0
        for i, pb in enumerate(prov_brackets):
            p_rate = prov_rates[i] if i < len(prov_rates) else prov_rates[-1]
            prov_lines.append(f"  - Tier {i+1}: Taxable income from ${prev_p:,.2f} up to ${pb:,.2f} is taxed at {p_rate*100:.2f}%")
            prev_p = pb
        last_p_rate = prov_rates[-1] if prov_rates else 0.1316
        prov_lines.append(f"  - Top Tier: Taxable income over ${prov_brackets[-1]:,.2f} is taxed at {last_p_rate*100:.2f}%")

        tk.Label(prov_card, text="\n".join(prov_lines), bg="#FFFFFF", fg="#334155", font=("Consolas", 9), justify=tk.LEFT).pack(anchor=tk.W, padx=12, pady=(0, 8))

    def _build_json_tab(self, parent):
        editor_frame = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(
            editor_frame,
            text="Raw JSON Threshold Database (Advanced Editing):",
            bg="#FFFFFF",
            fg="#0F172A",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(10, 4))

        self.text_area = tk.Text(editor_frame, wrap=tk.WORD, font=("Consolas", 10), bg="#F8FAFC", fg="#0F172A", height=18)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self._load_json_to_text()

        btn_row = tk.Frame(parent, bg="#F0F4F8")
        btn_row.pack(fill=tk.X, pady=6)

        save_btn = tk.Button(
            btn_row,
            text="💾 Save & Apply New Thresholds",
            bg="#16A34A",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._save_thresholds,
        )
        save_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(
            btn_row,
            text="Close",
            bg="#334155",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.top.destroy,
        )
        close_btn.pack(side=tk.RIGHT)

    def _load_json_to_text(self):
        try:
            data = load_tax_thresholds()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", json.dumps(data, indent=4))
        except Exception as e:
            self.text_area.insert("1.0", f"Error loading JSON: {e}")

    def _save_thresholds(self):
        raw_text = self.text_area.get("1.0", tk.END)
        try:
            parsed = json.loads(raw_text)
            with open(THRESHOLD_FILE, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=4)
            messagebox.showinfo("Success", "Tax thresholds successfully updated and saved! The calculation engine has updated.")
            self.app_instance.refresh_tax_years()
            self.top.destroy()
        except json.JSONDecodeError as err:
            messagebox.showerror("Invalid JSON", f"Please check your JSON syntax formatting.\n\nError: {err}")


class TaxCalculationBreakdownWindow:
    def __init__(self, parent: tk.Tk, res: TaxAndNetResult):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Detailed Tax Calculation Breakdown - {res.name} ({res.tax_year})")
        self.top.geometry("780x680")
        self.top.minsize(700, 600)
        self.top.configure(bg="#F0F4F8")

        header = tk.Frame(self.top, bg="#1E293B", height=64)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"🧮 Step-by-Step Tax Calculation ({res.tax_year}): {res.name}",
            bg="#1E293B",
            fg="#FFFFFF",
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=20, pady=16)

        container = tk.Frame(self.top, bg="#F0F4F8")
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        canvas = tk.Canvas(container, bg="#F0F4F8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#F0F4F8")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._add_section_card(scrollable_frame, "1. Gross Income & Taxable Income", [
            f"• Tax Year Engine Used: {res.tax_year}",
            f"• Total Annual Gross Income: ${res.gross_income:,.2f}",
            f"• Less PSSA Pension Deductions (Box 20 RPP): -${res.pssa_deduction:,.2f}",
            f"• Less Union Dues (Box 44): -${res.union_dues:,.2f}",
            f"👉 Final Taxable Income: ${res.taxable_income:,.2f}"
        ], "#2563EB")

        self._add_section_card(scrollable_frame, f"2. Federal Gross Tax ({res.tax_year} Brackets)", res.fed_steps + [
            f"👉 Total Federal Gross Tax: ${res.fed_tax_gross:,.2f}"
        ], "#0D9488")

        self._add_section_card(scrollable_frame, f"3. Ontario Provincial Gross Tax ({res.tax_year} Brackets)", res.prov_steps + [
            f"👉 Total Ontario Provincial Gross Tax: ${res.prov_tax_gross:,.2f}"
        ], "#4F46E5")

        self._add_section_card(scrollable_frame, "4. Non-Refundable Tax Credits & Savings", res.credit_steps + [
            f"• Federal BPA Credit: -${res.fed_bpa_credit_amt:,.2f}",
            f"• Ontario BPA Credit: -${res.prov_bpa_credit_amt:,.2f}",
            f"• Federal Pension Credit: -${res.fed_pension_credit_amt:,.2f}",
            f"• Ontario Pension Credit: -${res.prov_pension_credit_amt:,.2f}",
            f"• Federal Age Credit: -${res.fed_age_credit_amt:,.2f} (Clawback: ${res.fed_age_clawback_amt:,.2f})",
            f"• Ontario Age Credit: -${res.prov_age_credit_amt:,.2f}",
            f"👉 Total Credit Savings Applied: -${res.total_credits_savings:,.2f}"
        ], "#16A34A")

        self._add_section_card(scrollable_frame, "5. Surtaxes, Health Premium & Final Net Tax", [
            f"• Net Federal Tax (Gross minus Credits): ${res.fed_tax_net:,.2f}",
            f"• Basic Provincial Net Tax: ${res.prov_basic_net:,.2f}",
            f"• Ontario Surtax: ${res.ontario_surtax:,.2f}",
            f"• Ontario Health Premium (OHP): ${res.health_premium:,.2f}",
            f"• Net Provincial Tax (including Surtax & OHP): ${res.prov_tax_net:,.2f}",
            f"👉 TOTAL NET TAX PAYABLE: ${res.total_tax:,.2f} ({res.effective_tax_rate:.1f}% Effective Rate)"
        ], "#DC2626")

        close_btn = tk.Button(
            self.top,
            text="Close Window",
            bg="#334155",
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.top.destroy,
        )
        close_btn.pack(side=tk.BOTTOM, pady=12)

    def _add_section_card(self, parent, title: str, lines: List[str], accent_color: str):
        card = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 12), ipadx=8, ipady=6)

        strip = tk.Frame(card, bg=accent_color, height=4)
        strip.pack(fill=tk.X)

        tk.Label(
            card,
            text=title,
            bg="#FFFFFF",
            fg="#0F172A",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(8, 4))

        for line in lines:
            tk.Label(
                card,
                text=line,
                bg="#FFFFFF",
                fg="#334155",
                font=("Segoe UI", 9),
                anchor=tk.W,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=20, pady=2)


class RetirementCalculatorApp:
    BG_MAIN = "#F0F4F8"
    BG_HEADER = "#1E293B"
    BG_CARD = "#FFFFFF"
    ACCENT_BLUE = "#2563EB"
    ACCENT_TEAL = "#0D9488"
    ACCENT_INDIGO = "#4F46E5"
    TEXT_DARK = "#0F172A"
    TEXT_MUTED = "#475569"
    ROW_ALT = "#F8FAFC"
    HIGHLIGHT_GREEN = "#DCFCE7"
    HIGHLIGHT_GREEN_TEXT = "#166534"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Canadian Retirement & Cash Flow Planner (Dynamic Tax Threshold Engine)")
        self.root.geometry("1280x900")
        self.root.minsize(1100, 750)
        self.root.configure(bg=self.BG_MAIN)

        self.custom_scenarios: List[ScenarioInput] = []
        self.preset_results_map = {}
        self._setup_styles()
        self._build_header()
        self._build_notebook()

    def refresh_tax_years(self):
        pass

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=self.BG_MAIN, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#CBD5E1",
            foreground=self.TEXT_DARK,
            padding=[18, 10],
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.ACCENT_BLUE)],
            foreground=[("selected", "#FFFFFF")],
        )

        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=self.TEXT_DARK,
            rowheight=30,
            fieldbackground="#FFFFFF",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#334155",
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#1E3A8A")])

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg=self.BG_HEADER, height=76)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="🍁 Canadian Public Service & Healthcare Retirement Calculator",
            bg=self.BG_HEADER,
            fg="#FFFFFF",
            font=("Segoe UI", 16, "bold"),
        )
        title_lbl.pack(side=tk.LEFT, padx=24, pady=18)

        threshold_mgr_btn = tk.Button(
            header_frame,
            text="⚙️ Manage Tax Thresholds & Sources",
            bg=self.ACCENT_TEAL,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: TaxThresholdManagerWindow(self.root, self),
        )
        threshold_mgr_btn.pack(side=tk.RIGHT, padx=24)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        self.tab_paula = tk.Frame(self.notebook, bg=self.BG_MAIN)
        self.notebook.add(self.tab_paula, text="  👩‍⚕️ Paula's Scenarios (CalcPaula)  ")
        self._build_preset_tab(
            self.tab_paula,
            "Paula's Hospital Shift & Retirement Scenarios (Selectable Tax Year)",
            get_paula_presets(),
            "paula_retirement_scenarios.csv",
            accent_color=self.ACCENT_TEAL,
            tab_key="paula"
        )

        self.tab_randy = tk.Frame(self.notebook, bg=self.BG_MAIN)
        self.notebook.add(self.tab_randy, text="  👨‍💻 Randy's Scenarios (GoC IT-03 / PRTL)  ")
        self._build_preset_tab(
            self.tab_randy,
            "Randy's GoC IT-03, PRTL & November Retirement Scenarios",
            get_randy_presets(),
            "randy_retirement_scenarios.csv",
            accent_color=self.ACCENT_BLUE,
            tab_key="randy"
        )

        self.tab_sandbox = tk.Frame(self.notebook, bg=self.BG_MAIN)
        self.notebook.add(self.tab_sandbox, text="  🎛️ Interactive Scenario Sandbox (T4 Slip Entry)  ")
        self._build_sandbox_tab(self.tab_sandbox)

    def _build_preset_tab(
        self,
        parent: tk.Frame,
        banner_title: str,
        presets: List[ScenarioInput],
        default_csv: str,
        accent_color: str,
        tab_key: str,
    ):
        results = [calculate_ontario_tax_and_net(s) for s in presets]
        self.preset_results_map[tab_key] = results

        top_bar = tk.Frame(parent, bg=self.BG_CARD, bd=1, relief=tk.SOLID)
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 8))

        tk.Label(
            top_bar,
            text=banner_title,
            bg=self.BG_CARD,
            fg=self.TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
        ).pack(side=tk.LEFT, padx=16, pady=12)

        btn_group = tk.Frame(top_bar, bg=self.BG_CARD)
        btn_group.pack(side=tk.RIGHT, padx=16, pady=6)

        export_btn = tk.Button(
            btn_group,
            text="📥 Export Table to CSV",
            bg=accent_color,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self._export_csv_dialog(results, default_csv),
        )
        export_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.selected_scenario_var = tk.StringVar(value=results[0].name)
        scenario_names = [r.name for r in results]
        
        breakdown_btn = tk.Button(
            btn_group,
            text="🧮 View Tax Calculation Breakdown",
            bg=self.ACCENT_INDIGO,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
            command=lambda: self._open_breakdown_for_preset(tab_key),
        )
        breakdown_btn.pack(side=tk.RIGHT, padx=(6, 6))

        self.scenario_combo_map = getattr(self, "scenario_combo_map", {})
        combo = ttk.Combobox(btn_group, textvariable=self.selected_scenario_var, values=scenario_names, state="readonly", width=28)
        combo.pack(side=tk.RIGHT, padx=(6, 6))
        self.scenario_combo_map[tab_key] = combo

        cards_frame = tk.Frame(parent, bg=self.BG_MAIN)
        cards_frame.pack(fill=tk.X, padx=10, pady=6)

        for idx, res in enumerate(results):
            card = tk.Frame(cards_frame, bg=self.BG_CARD, highlightbackground="#CBD5E1", highlightthickness=1)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if idx == 0 else 6, 0))

            strip = tk.Frame(card, bg=accent_color if idx % 2 == 0 else self.ACCENT_INDIGO, height=5)
            strip.pack(fill=tk.X)

            tk.Label(
                card,
                text=res.name,
                bg=self.BG_CARD,
                fg=self.TEXT_MUTED,
                font=("Segoe UI", 9, "bold"),
                wraplength=190,
            ).pack(pady=(8, 2), padx=8)

            tk.Label(
                card,
                text=f"${res.annual_net_cash:,.2f}/yr",
                bg=self.BG_CARD,
                fg=self.HIGHLIGHT_GREEN_TEXT,
                font=("Segoe UI", 13, "bold"),
            ).pack(pady=2)

            tk.Label(
                card,
                text=f"Year {res.tax_year} | Tax: {res.effective_tax_rate:.1f}%",
                bg=self.BG_CARD,
                fg=self.TEXT_DARK,
                font=("Segoe UI", 9),
            ).pack(pady=(2, 10))

        table_container = tk.Frame(parent, bg=self.BG_CARD, bd=1, relief=tk.SOLID)
        table_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 10))

        columns = ["metric"] + [f"col_{i}" for i in range(len(results))]
        tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        tree.heading("metric", text="Financial / Tax Line Item", anchor=tk.W)
        tree.column("metric", width=260, anchor=tk.W)

        for i, res in enumerate(results):
            col_id = f"col_{i}"
            tree.heading(col_id, text=res.name, anchor=tk.E)
            tree.column(col_id, width=175, anchor=tk.E)

        tree.tag_configure("odd", background="#FFFFFF")
        tree.tag_configure("even", background=self.ROW_ALT)
        tree.tag_configure("highlight", background=self.HIGHLIGHT_GREEN, foreground=self.HIGHLIGHT_GREEN_TEXT, font=("Segoe UI", 10, "bold"))
        tree.tag_configure("boldrow", background="#E2E8F0", font=("Segoe UI", 10, "bold"))

        rows = [
            ("Tax Year Threshold Engine Used", [f"{r.tax_year}" for r in results], "boldrow"),
            ("Annual Gross Income", [f"${r.gross_income:,.2f}" for r in results], "boldrow"),
            ("PSSA Pension Contribution (Box 20 RPP)", [f"-${r.pssa_deduction:,.2f}" for r in results], "odd"),
            ("Union Dues (Box 44)", [f"-${r.union_dues:,.2f}" for r in results], "even"),
            ("CPP1 Contributions - Base (Box 16)", [f"-${r.cpp1_deduction:,.2f}" for r in results], "odd"),
            ("CPP2 Contributions - Additional (Box 16A)", [f"-${r.cpp2_deduction:,.2f}" for r in results], "even"),
            ("EI Premiums (Box 18)", [f"-${r.ei_deduction:,.2f}" for r in results], "even"),
            ("Federal BPA Credit", [f"-${r.fed_bpa_credit_amt:,.2f}" for r in results], "odd"),
            ("Ontario BPA Credit", [f"-${r.prov_bpa_credit_amt:,.2f}" for r in results], "even"),
            ("Federal Pension Credit", [f"-${r.fed_pension_credit_amt:,.2f}" for r in results], "odd"),
            ("Ontario Pension Credit", [f"-${r.prov_pension_credit_amt:,.2f}" for r in results], "even"),
            ("Federal Age Credit (Net of Clawback)", [f"-${r.fed_age_credit_amt:,.2f}" for r in results], "odd"),
            ("Ontario Age Credit", [f"-${r.prov_age_credit_amt:,.2f}" for r in results], "even"),
            ("Federal Age Credit Clawback", [f"${r.fed_age_clawback_amt:,.2f}" for r in results], "odd"),
            ("Total Tax Savings from Credits", [f"-${r.total_credits_savings:,.2f}" for r in results], "boldrow"),
            ("Federal Income Tax (Net)", [f"${r.fed_tax_net:,.2f}" for r in results], "odd"),
            ("Provincial Income Tax (Basic Net)", [f"${r.prov_basic_net:,.2f}" for r in results], "even"),
            ("Ontario Surtax", [f"${r.ontario_surtax:,.2f}" for r in results], "odd"),
            ("Ontario Health Premium (OHP)", [f"${r.health_premium:,.2f}" for r in results], "even"),
            ("Provincial Tax (Total incl. Surtax & OHP)", [f"${r.prov_tax_net:,.2f}" for r in results], "even"),
            ("TOTAL ANNUAL TAX PAID", [f"-${r.total_tax:,.2f}" for r in results], "boldrow"),
            ("Effective Tax Rate (%)", [f"{r.effective_tax_rate:.2f}%" for r in results], "odd"),
            ("Other Expenses (Bus/Lunch/Fuel/Lottery)", [f"-${r.other_deductions:,.2f}" for r in results], "even"),
            ("TOTAL ANNUAL DEDUCTIONS & EXPENSES", [f"-${r.total_deductions:,.2f}" for r in results], "boldrow"),
            ("ANNUAL NET TAKE-HOME PAY", [f"${r.annual_net_cash:,.2f}" for r in results], "highlight"),
            ("MONTHLY NET CASH FLOW", [f"${r.monthly_net_cash:,.2f}" for r in results], "highlight"),
            ("BI-WEEKLY NET PAYCHEQUE", [f"${r.biweekly_net_cash:,.2f}" for r in results], "highlight"),
        ]

        for label, values, tag in rows:
            tree.insert("", tk.END, values=[label] + values, tags=(tag,))

        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _open_breakdown_for_preset(self, tab_key: str):
        combo = self.scenario_combo_map.get(tab_key)
        selected_name = combo.get()
        results = self.preset_results_map.get(tab_key, [])
        target_res = next((r for r in results if r.name == selected_name), results[0])
        TaxCalculationBreakdownWindow(self.root, target_res)

    def _build_sandbox_tab(self, parent: tk.Frame):
        main_pane = tk.Frame(parent, bg=self.BG_MAIN)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_panel = tk.Frame(main_pane, bg=self.BG_CARD, width=480, bd=1, relief=tk.SOLID)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(
            left_panel,
            text="🎛️ Configure Custom Scenario (Tax Year & T4 Slip)",
            bg="#1E293B",
            fg="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            pady=10,
        ).pack(fill=tk.X)

        form_canvas = tk.Canvas(left_panel, bg=self.BG_CARD, highlightthickness=0)
        form_scroll = ttk.Scrollbar(left_panel, orient="vertical", command=form_canvas.yview)
        form_frame = tk.Frame(form_canvas, bg=self.BG_CARD)

        form_frame.bind(
            "<Configure>",
            lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        )
        form_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_canvas.configure(yscrollcommand=form_scroll.set)

        form_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=6)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.var_profile = tk.StringVar(value="Paula Preset (Hospital Shift)")
        self.var_name = tk.StringVar(value="Custom Scenario A")
        self.var_tax_year = tk.StringVar(value="2026")
        self.var_age = tk.IntVar(value=64)
        self.var_working = tk.BooleanVar(value=True)
        
        self.var_t4_box14 = tk.DoubleVar(value=91610.75)
        self.var_t4_box16_cpp1 = tk.DoubleVar(value=4230.45)
        self.var_t4_box16_cpp2 = tk.DoubleVar(value=416.00)
        self.var_t4_box18 = tk.DoubleVar(value=1050.0)
        self.var_t4_box20 = tk.DoubleVar(value=5498.83)
        self.var_t4_box22 = tk.DoubleVar(value=16009.57)
        self.var_t4_box44 = tk.DoubleVar(value=1490.28)
        self.var_t4_box52 = tk.DoubleVar(value=91610.75 * 0.02)
        
        self.var_pension = tk.DoubleVar(value=0.0)
        self.var_cpp = tk.DoubleVar(value=17280.0)
        self.var_oas = tk.DoubleVar(value=0.0)
        self.var_rrsp = tk.DoubleVar(value=0.0)
        
        self.var_bus = tk.DoubleVar(value=0.0)
        self.var_lunch = tk.DoubleVar(value=1500.0)
        self.var_parking = tk.DoubleVar(value=1200.0)
        self.var_fuel = tk.DoubleVar(value=0.0)
        self.var_lottery = tk.DoubleVar(value=0.0)
        self.var_other_exp = tk.DoubleVar(value=0.0)

        thresholds_db = load_tax_thresholds()
        available_years = sorted(list(thresholds_db.keys()), reverse=True)

        tk.Label(form_frame, text="Quick-Load Template:", bg=self.BG_CARD, fg=self.TEXT_DARK, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=4)
        profile_combo = ttk.Combobox(
            form_frame,
            textvariable=self.var_profile,
            state="readonly",
            values=[
                "Paula Preset (4-Day Shift + CPP)",
                "Paula Preset (Retire @ 64 + $15k RRSP)",
                "Randy Preset (PRTL 4-Day + CPP)",
                "Randy Preset (Full Retire @ 65)",
            ],
            width=24,
        )
        profile_combo.grid(row=0, column=1, sticky=tk.E, pady=4)
        profile_combo.bind("<<ComboboxSelected>>", self._on_template_selected)

        fields = [
            ("Scenario Label:", self.var_name, "entry", "Custom name for this scenario"),
            ("Tax Year Threshold Engine:", self.var_tax_year, "combo_year", "Select published tax year brackets"),
            ("Age in Tax Year:", self.var_age, "spin_age", "Used for Age 65+ tax credits"),
            ("T4 Box 14 - Employment Income ($):", self.var_t4_box14, "entry", "Total employment income before deductions"),
            ("T4 Box 16 - CPP1 Base Contributions ($):", self.var_t4_box16_cpp1, "entry", "Base CPP contributions (up to YMPE)"),
            ("T4 Box 16A - CPP2 Additional Contributions ($):", self.var_t4_box16_cpp2, "entry", "Second additional CPP contributions (YAMPE)"),
            ("T4 Box 18 - Employee EI Premiums ($):", self.var_t4_box18, "entry", "Employment Insurance premiums"),
            ("T4 Box 20 - RPP Contributions ($):", self.var_t4_box20, "entry", "Registered Pension Plan / PSSA deductions"),
            ("T4 Box 22 - Income Tax Deducted ($):", self.var_t4_box22, "entry", "Actual tax deducted (leave 0 for auto-calculation)"),
            ("T4 Box 44 - Union Dues ($):", self.var_t4_box44, "entry", "Union dues paid"),
            ("T4 Box 52 - Pension Adjustment ($):", self.var_t4_box52, "entry", "Pension adjustment for RRSP room"),
            ("Other Pension Income ($):", self.var_pension, "entry", "Defined benefit pension in retirement"),
            ("CPP Retirement Income ($):", self.var_cpp, "entry", "Canada Pension Plan benefits"),
            ("OAS Retirement Income ($):", self.var_oas, "entry", "Old Age Security benefits"),
            ("RRSP Withdrawal ($):", self.var_rrsp, "entry", "Taxable RRSP / RRIF withdrawals"),
            ("Bus Fare / Transit ($):", self.var_bus, "entry", "Annual public transit / bus pass expenses"),
            ("Lunch / Meals ($):", self.var_lunch, "entry", "Annual work shift meals / coffee"),
            ("Parking Fee ($):", self.var_parking, "entry", "Workplace parking fees"),
            ("Vehicle Fuel ($):", self.var_fuel, "entry", "Commuting & vehicle fuel expenses"),
            ("Lottery ($):", self.var_lottery, "entry", "Annual lottery / discretionary spending"),
            ("Other General Expenses ($):", self.var_other_exp, "entry", "Any other miscellaneous out-of-pocket costs"),
        ]

        row_idx = 1
        chk = tk.Checkbutton(
            form_frame,
            text="Currently Working (Include T4 Employment & CPP/EI)",
            variable=self.var_working,
            bg=self.BG_CARD,
            fg=self.ACCENT_BLUE,
            font=("Segoe UI", 9, "bold"),
            command=self._recalculate_sandbox,
        )
        chk.grid(row=row_idx, column=0, columnspan=2, sticky=tk.W, pady=6)
        row_idx += 1

        for label_text, var, widget_type, tooltip in fields:
            lbl = tk.Label(form_frame, text=label_text, bg=self.BG_CARD, fg=self.TEXT_DARK, font=("Segoe UI", 9))
            lbl.grid(row=row_idx, column=0, sticky=tk.W, pady=(4, 0))
            
            sub_lbl = tk.Label(form_frame, text=tooltip, bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 8, "italic"))
            sub_lbl.grid(row=row_idx+1, column=0, sticky=tk.W, pady=(0, 4))

            if widget_type == "spin_age":
                w = tk.Spinbox(form_frame, from_=55, to=80, textvariable=var, width=22, font=("Segoe UI", 9), command=self._recalculate_sandbox)
            elif widget_type == "combo_year":
                w = ttk.Combobox(form_frame, textvariable=var, values=available_years, state="readonly", width=21)
                w.bind("<<ComboboxSelected>>", lambda e: self._recalculate_sandbox())
            else:
                w = tk.Entry(form_frame, textvariable=var, width=24, font=("Segoe UI", 9))
            w.grid(row=row_idx, column=1, rowspan=2, sticky=tk.E, pady=4)
            row_idx += 2

        btn_frame = tk.Frame(left_panel, bg=self.BG_CARD)
        btn_frame.pack(fill=tk.X, padx=16, pady=12)

        calc_btn = tk.Button(
            btn_frame,
            text="🔄 Calculate",
            bg=self.ACCENT_BLUE,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=8,
            cursor="hand2",
            command=self._recalculate_sandbox,
        )
        calc_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        breakdown_btn = tk.Button(
            btn_frame,
            text="🧮 Tax Math",
            bg=self.ACCENT_INDIGO,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=8,
            cursor="hand2",
            command=self._open_sandbox_breakdown,
        )
        breakdown_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 4))

        pin_btn = tk.Button(
            btn_frame,
            text="📌 Pin",
            bg=self.ACCENT_TEAL,
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=8,
            pady=8,
            cursor="hand2",
            command=self._pin_sandbox_scenario,
        )
        pin_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        self.right_sandbox_panel = tk.Frame(main_pane, bg=self.BG_MAIN)
        self.right_sandbox_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._recalculate_sandbox()

    def _on_template_selected(self, event=None):
        sel = self.var_profile.get()
        if "Paula Preset (4-Day" in sel:
            self.var_name.set("Paula 4-Day + CPP")
            self.var_tax_year.set("2026")
            self.var_age.set(64)
            self.var_working.set(True)
            self.var_t4_box14.set(69006.00)
            self.var_t4_box16_cpp1.set(3897.60)
            self.var_t4_box16_cpp2.set(0.0)
            self.var_t4_box18.set(950.0)
            self.var_t4_box20.set(69006.00 * (5498.83 / 91610.75))
            self.var_t4_box22.set(10159.86)
            self.var_t4_box44.set(69006.00 * (1490.28 / 91610.75))
            self.var_pension.set(0.0)
            self.var_cpp.set(17280.0)
            self.var_oas.set(0.0)
            self.var_rrsp.set(0.0)
            self.var_bus.set(0.0)
            self.var_lunch.set(1200.0)
            self.var_parking.set(960.0)
            self.var_fuel.set(0.0)
            self.var_lottery.set(0.0)
        elif "Paula Preset (Retire @ 64" in sel:
            self.var_name.set("Paula Retire + $15k RRSP")
            self.var_tax_year.set("2026")
            self.var_age.set(64)
            self.var_working.set(False)
            self.var_t4_box14.set(0.0)
            self.var_t4_box22.set(0.0)
            self.var_pension.set(37200.0)
            self.var_cpp.set(17280.0)
            self.var_oas.set(0.0)
            self.var_rrsp.set(15000.0)
            self.var_bus.set(0.0)
            self.var_lunch.set(0.0)
            self.var_parking.set(0.0)
            self.var_fuel.set(0.0)
            self.var_lottery.set(0.0)
        elif "Randy Preset (PRTL" in sel:
            self.var_name.set("Randy PRTL 4-Day")
            self.var_tax_year.set("2026")
            self.var_age.set(65)
            self.var_working.set(True)
            self.var_t4_box14.set(100891.91)
            self.var_t4_box16_cpp1.set(4230.45)
            self.var_t4_box16_cpp2.set(416.00)
            self.var_t4_box18.set(1050.0)
            self.var_t4_box20.set(12777.49 * (100891.91 / 126114.89))
            self.var_t4_box22.set(19500.0)
            self.var_t4_box44.set(1080.72 * (100891.91 / 126114.89))
            self.var_pension.set(0.0)
            self.var_cpp.set(18091.80)
            self.var_oas.set(0.0)
            self.var_rrsp.set(0.0)
            self.var_bus.set(0.0)
            self.var_lunch.set(0.0)
            self.var_parking.set(1440.0)
            self.var_fuel.set(1920.0)
            self.var_lottery.set(0.0)
        elif "Randy Preset (Full Retire" in sel:
            self.var_name.set("Randy Retire @ 65")
            self.var_tax_year.set("2026")
            self.var_age.set(65)
            self.var_working.set(False)
            self.var_t4_box14.set(0.0)
            self.var_t4_box22.set(0.0)
            self.var_pension.set(53607.96)
            self.var_cpp.set(18091.80)
            self.var_oas.set(9023.64)
            self.var_rrsp.set(521.0)
            self.var_bus.set(0.0)
            self.var_lunch.set(0.0)
            self.var_parking.set(0.0)
            self.var_fuel.set(0.0)
            self.var_lottery.set(0.0)

        self._recalculate_sandbox()

    def _build_current_sandbox_input(self) -> ScenarioInput:
        try:
            emp = float(self.var_t4_box14.get()) if self.var_working.get() else 0.0
            return ScenarioInput(
                name=self.var_name.get().strip() or "Custom T4 Scenario",
                category="Custom",
                employment_income=emp,
                pension_income=float(self.var_pension.get()),
                cpp_income=float(self.var_cpp.get()),
                oas_income=float(self.var_oas.get()),
                rrsp_withdrawal=float(self.var_rrsp.get()),
                age=int(self.var_age.get()),
                is_working=self.var_working.get(),
                tax_year=self.var_tax_year.get(),
                t4_box14_employment=float(self.var_t4_box14.get()),
                t4_box16_cpp1=float(self.var_t4_box16_cpp1.get()),
                t4_box16_cpp2=float(self.var_t4_box16_cpp2.get()),
                t4_box18_ei=float(self.var_t4_box18.get()),
                t4_box20_rpp=float(self.var_t4_box20.get()),
                t4_box22_tax_deducted=float(self.var_t4_box22.get()) if self.var_working.get() else 0.0,
                t4_box44_union=float(self.var_t4_box44.get()),
                t4_box52_pa=float(self.var_t4_box52.get()),
                exp_bus=float(self.var_bus.get()),
                exp_lunch=float(self.var_lunch.get()),
                exp_parking=float(self.var_parking.get()),
                exp_fuel=float(self.var_fuel.get()),
                exp_lottery=float(self.var_lottery.get()),
                exp_other=float(self.var_other_exp.get()),
            )
        except Exception as exc:
            messagebox.showerror("Input Error", f"Please verify all numeric inputs. Details: {exc}")
            return ScenarioInput(name="Error", category="Custom")

    def _recalculate_sandbox(self):
        for widget in self.right_sandbox_panel.winfo_children():
            widget.destroy()

        current_input = self._build_current_sandbox_input()
        self.current_active_result = calculate_ontario_tax_and_net(current_input)
        all_results = [self.current_active_result] + [calculate_ontario_tax_and_net(s) for s in self.custom_scenarios]
        active_res = self.current_active_result

        hero = tk.Frame(self.right_sandbox_panel, bg=self.BG_CARD, bd=1, relief=tk.SOLID)
        hero.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            hero,
            text=f"Live Projection: {active_res.name} (Tax Year: {active_res.tax_year})",
            bg=self.BG_CARD,
            fg=self.TEXT_DARK,
            font=("Segoe UI", 12, "bold"),
        ).pack(side=tk.LEFT, padx=16, pady=12)

        if self.custom_scenarios:
            clear_btn = tk.Button(
                hero,
                text="🗑️ Clear Pinned",
                bg="#EF4444",
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                padx=10,
                pady=4,
                cursor="hand2",
                command=self._clear_pinned,
            )
            clear_btn.pack(side=tk.RIGHT, padx=12)

        kpi_row = tk.Frame(self.right_sandbox_panel, bg=self.BG_MAIN)
        kpi_row.pack(fill=tk.X, pady=(0, 8))

        kpis = [
            ("Annual Gross Income", f"${active_res.gross_income:,.2f}", self.ACCENT_BLUE),
            (f"Total Tax ({active_res.tax_year})", f"-${active_res.total_tax:,.2f} ({active_res.effective_tax_rate:.1f}%)", "#DC2626"),
            ("Annual Net Take-Home", f"${active_res.annual_net_cash:,.2f}", "#16A34A"),
            ("Monthly / Bi-Weekly Net", f"${active_res.monthly_net_cash:,.2f}/mo  |  ${active_res.biweekly_net_cash:,.2f}/bw", self.ACCENT_INDIGO),
        ]

        for idx, (lbl, val, color) in enumerate(kpis):
            box = tk.Frame(kpi_row, bg=self.BG_CARD, highlightbackground="#CBD5E1", highlightthickness=1)
            box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0 if idx == 0 else 6, 0))
            tk.Frame(box, bg=color, height=4).pack(fill=tk.X)
            tk.Label(box, text=lbl, bg=self.BG_CARD, fg=self.TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(pady=(6, 2))
            tk.Label(box, text=val, bg=self.BG_CARD, fg=color, font=("Segoe UI", 11, "bold")).pack(pady=(0, 8))

        tbl_frame = tk.Frame(self.right_sandbox_panel, bg=self.BG_CARD, bd=1, relief=tk.SOLID)
        tbl_frame.pack(fill=tk.BOTH, expand=True)

        cols = ["metric"] + [f"s_{i}" for i in range(len(all_results))]
        tree = ttk.Treeview(tbl_frame, columns=cols, show="headings")
        tree.heading("metric", text="Line Item & Tax Year", anchor=tk.W)
        tree.column("metric", width=260, anchor=tk.W)

        for i, r in enumerate(all_results):
            cid = f"s_{i}"
            label = f"▶ {r.name} (Active)" if i == 0 else f"📌 {r.name}"
            tree.heading(cid, text=label, anchor=tk.E)
            tree.column(cid, width=175, anchor=tk.E)

        tree.tag_configure("odd", background="#FFFFFF")
        tree.tag_configure("even", background=self.ROW_ALT)
        tree.tag_configure("highlight", background=self.HIGHLIGHT_GREEN, foreground=self.HIGHLIGHT_GREEN_TEXT, font=("Segoe UI", 10, "bold"))
        tree.tag_configure("boldrow", background="#E2E8F0", font=("Segoe UI", 10, "bold"))

        rows = [
            ("Tax Year Threshold Engine Used", [f"{r.tax_year}" for r in all_results], "boldrow"),
            ("Annual Gross Income", [f"${r.gross_income:,.2f}" for r in all_results], "boldrow"),
            ("PSSA Pension Deduction (Box 20 RPP)", [f"-${r.pssa_deduction:,.2f}" for r in all_results], "odd"),
            ("Union Dues (Box 44)", [f"-${r.union_dues:,.2f}" for r in all_results], "even"),
            ("CPP1 Contributions - Base (Box 16)", [f"-${r.cpp1_deduction:,.2f}" for r in all_results], "odd"),
            ("CPP2 Contributions - Additional (Box 16A)", [f"-${r.cpp2_deduction:,.2f}" for r in all_results], "even"),
            ("EI Premiums (Box 18)", [f"-${r.ei_deduction:,.2f}" for r in all_results], "even"),
            ("Federal BPA Credit", [f"-${r.fed_bpa_credit_amt:,.2f}" for r in all_results], "odd"),
            ("Ontario BPA Credit", [f"-${r.prov_bpa_credit_amt:,.2f}" for r in all_results], "even"),
            ("Federal Pension Credit", [f"-${r.fed_pension_credit_amt:,.2f}" for r in all_results], "odd"),
            ("Ontario Pension Credit", [f"-${r.prov_pension_credit_amt:,.2f}" for r in all_results], "even"),
            ("Federal Age Credit (Net of Clawback)", [f"-${r.fed_age_credit_amt:,.2f}" for r in all_results], "odd"),
            ("Ontario Age Credit", [f"-${r.prov_age_credit_amt:,.2f}" for r in all_results], "even"),
            ("Federal Age Credit Clawback", [f"${r.fed_age_clawback_amt:,.2f}" for r in all_results], "odd"),
            ("Total Tax Savings from Credits", [f"-${r.total_credits_savings:,.2f}" for r in all_results], "boldrow"),
            ("Federal Income Tax (Net)", [f"${r.fed_tax_net:,.2f}" for r in all_results], "odd"),
            ("Provincial Income Tax (Basic Net)", [f"${r.prov_basic_net:,.2f}" for r in all_results], "even"),
            ("Ontario Surtax", [f"${r.ontario_surtax:,.2f}" for r in all_results], "odd"),
            ("Ontario Health Premium (OHP)", [f"${r.health_premium:,.2f}" for r in all_results], "even"),
            ("Provincial Tax (Total incl. Surtax & OHP)", [f"${r.prov_tax_net:,.2f}" for r in all_results], "even"),
            ("Total Tax Liability", [f"-${r.total_tax:,.2f}" for r in all_results], "boldrow"),
            ("Other Expenses (Bus/Lunch/Fuel/Lottery)", [f"-${r.other_deductions:,.2f}" for r in all_results], "odd"),
            ("TOTAL ANNUAL DEDUCTIONS & EXPENSES", [f"-${r.total_deductions:,.2f}" for r in all_results], "boldrow"),
            ("ANNUAL NET TAKE-HOME", [f"${r.annual_net_cash:,.2f}" for r in all_results], "highlight"),
            ("MONTHLY NET CASH", [f"${r.monthly_net_cash:,.2f}" for r in all_results], "highlight"),
            ("BI-WEEKLY NET PAY", [f"${r.biweekly_net_cash:,.2f}" for r in all_results], "highlight"),
        ]

        for lbl, vals, tag in rows:
            tree.insert("", tk.END, values=[lbl] + vals, tags=(tag,))

        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _open_sandbox_breakdown(self):
        if hasattr(self, "current_active_result"):
            TaxCalculationBreakdownWindow(self.root, self.current_active_result)

    def _pin_sandbox_scenario(self):
        if len(self.custom_scenarios) >= 3:
            messagebox.showinfo("Limit Reached", "You can pin up to 3 scenarios side-by-side. Clear pinned items to add more.")
            return
        sc = self._build_current_sandbox_input()
        self.custom_scenarios.append(sc)
        self._recalculate_sandbox()

    def _clear_pinned(self):
        self.custom_scenarios.clear()
        self._recalculate_sandbox()

    def _export_csv_dialog(self, results: List[TaxAndNetResult], default_filename: str):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV Spreadsheets", "*.csv"), ("All Files", "*.*")],
        )
        if not filepath:
            return
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Scenario", "Tax Year", "Gross Income", "PSSA Pension (Box 20)", "Union Dues (Box 44)", "CPP1 (Box 16)", "CPP2 (Box 16A)", "EI (Box 18)",
                "Federal BPA Credit", "Ontario BPA Credit", "Federal Pension Credit", "Ontario Pension Credit", "Federal Age Credit", "Ontario Age Credit", "Federal Age Clawback", "Total Credit Savings",
                "Federal Net Tax", "Provincial Basic Net Tax", "Ontario Surtax", "Ontario Health Premium", "Provincial Net Tax", "Total Tax", "Effective Tax %",
                "Other Expenses", "Total Deductions", "Annual Net Cash", "Monthly Net Cash", "Bi-Weekly Net Cash"
            ])
            for r in results:
                writer.writerow([
                    r.name, r.tax_year, f"{r.gross_income:.2f}", f"{r.pssa_deduction:.2f}",
                    f"{r.union_dues:.2f}", f"{r.cpp1_deduction:.2f}", f"{r.cpp2_deduction:.2f}", f"{r.ei_deduction:.2f}",
                    f"{r.fed_bpa_credit_amt:.2f}", f"{r.prov_bpa_credit_amt:.2f}", f"{r.fed_pension_credit_amt:.2f}", f"{r.prov_pension_credit_amt:.2f}",
                    f"{r.fed_age_credit_amt:.2f}", f"{r.prov_age_credit_amt:.2f}", f"{r.fed_age_clawback_amt:.2f}", f"{r.total_credits_savings:.2f}",
                    f"{r.fed_tax_net:.2f}", f"{r.prov_basic_net:.2f}", f"{r.ontario_surtax:.2f}", f"{r.health_premium:.2f}", f"{r.prov_tax_net:.2f}", f"{r.total_tax:.2f}",
                    f"{r.effective_tax_rate:.2f}", f"{r.other_deductions:.2f}", f"{r.total_deductions:.2f}",
                    f"{r.annual_net_cash:.2f}", f"{r.monthly_net_cash:.2f}", f"{r.biweekly_net_cash:.2f}"
                ])
        messagebox.showinfo("Export Complete", f"Successfully exported table to: {filepath}")


def main():
    root = tk.Tk()
    app = RetirementCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()