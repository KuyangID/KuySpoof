#!/usr/bin/env python3
import csv
import json
import os
import re
import random
import urllib.request

# Configuration
CSV_URL = "https://storage.googleapis.com/play_public/supported_devices.csv"
CSV_PATH = "supported_devices.csv"
DB_PATH = "database"

# Android Build IDs & Incrementals
BUILD_MAP = {
    16: {"build": "BP4A.260205.001", "inc": "14624666"},
    15: {"build": "AP3A.241205.013", "inc": "12621605"},
    14: {"build": "UP1A.231005.007", "inc": "11480754"},
    13: {"build": "TP1A.220624.014", "inc": "10403759"},
    12: {"build": "SP1A.210812.016", "inc": "7769886"},
    11: {"build": "RP1A.200720.012", "inc": "6720843"},
    10: {"build": "QP1A.190711.020", "inc": "5765167"},
    9:  {"build": "PPR1.180905.001", "inc": "5456789"},
    8:  {"build": "OPR1.170623.032", "inc": "4523456"},
}

TARGET_BRANDS = [
    {"file": "samsung",  "match": "samsung"},
    {"file": "xiaomi",   "match": "xiaomi|redmi|poco|pocophone"},
    {"file": "oppo",     "match": "oppo"},
    {"file": "vivo",     "match": "vivo"},
    {"file": "realme",   "match": "realme"},
    {"file": "motorola", "match": "motorola"},
    {"file": "oneplus",  "match": "oneplus"},
    {"file": "asus",     "match": "asus"},
    {"file": "sony",     "match": "sony"},
    {"file": "google",   "match": "google"},
    {"file": "nokia",    "match": "nokia"},
    {"file": "huawei",   "match": "huawei"},
    {"file": "honor",    "match": "honor"},
    {"file": "infinix",  "match": "infinix"},
    {"file": "tecno",    "match": "tecno"},
    {"file": "advan",    "match": "advan"},
    {"file": "zte",      "match": "zte"},
    {"file": "lenovo",   "match": "lenovo"},
]

def get_android_version(brand, model, device):
    brand = brand.lower()
    m = model.upper()
    d = device.lower()

    if "samsung" in brand:
        # Modern S Series
        if re.search(r"SM-S93[0-9]", m): return 15
        if re.search(r"SM-S92[0-9]", m): return 14
        if re.search(r"SM-S91[0-9]", m): return 13
        if re.search(r"SM-S90[0-9]", m): return 12
        # Older S Series
        if re.search(r"SM-G99[0-9]", m): return 13
        if re.search(r"SM-G98[0-9]", m): return 12
        if re.search(r"SM-G97[0-9]", m): return 11
        if re.search(r"SM-G96[0-9]", m): return 10
        if re.search(r"SM-G95[0-9]", m): return 9
        if re.search(r"SM-G93[0-9]", m): return 8
        if re.search(r"SM-G9[012][0-9]", m): return 6
        # A Series
        if re.search(r"SM-A[357]5", m): return 15
        if re.search(r"SM-A[357]4", m): return 14
        if re.search(r"SM-A[357]3", m): return 13
        if re.search(r"SM-A[012][0-9]", m): return 12
        return 12
    
    if any(x in brand for x in ["xiaomi", "redmi", "poco"]):
        # Modern Xiaomi/Redmi/POCO (Model code usually starts with year: 23=2023, 22=2022)
        if re.search(r"^(24|25)", m): return 15
        if re.search(r"^23", m): return 14
        if re.search(r"^22", m): return 13
        if re.search(r"^21", m): return 12
        if re.search(r"^20", m): return 10
        # Codenames
        if re.search(r"^(alioth|vayu|bhima|munch|psyche)", d): return 12
        if re.search(r"^(marble|mondrian|fuxi|nuwa|thor|pissarro|ruby|fleur|topaz)", d): return 13
        if re.search(r"^(begonia|cepheus|raphael|davinci)", d): return 11
        return 11

    if "google" in brand:
        if re.search(r"^(sailfish|marlin)", d): return 10
        if re.search(r"^(shiba|husky|akita|tokay|caiman|komodo)", d): return 15
        if re.search(r"^(frankel|blazer|mustang|rango)", d): return 16
        return 14

    if "oneplus" in brand:
        if re.search(r"CPH2[56][0-9]{2}", m): return 15
        if re.search(r"CPH24[0-9]{2}", m): return 14
        return 13

    # Generic fallback
    if re.search(r"^2[45][0-9]{3}", m): return 15
    if re.search(r"^23[0-9]{3}", m): return 14
    return 12

def get_fingerprint(brand, model, device, android_ver):
    # Use build ID for version, fallback to 14 if not found
    ver = android_ver if android_ver in BUILD_MAP else 14
    b = BUILD_MAP[ver]
    bid = b["build"]
    inc = b["inc"]
    bl = brand.lower()

    if "samsung" in bl:
        suffix = "eub" if "B" in model.upper() else "xx"
        prod = f"{device}{suffix}"
        incr = model.replace("-", "") + "XXU1AWA1"
        return f"samsung/{prod}/{device}:{android_ver}/{bid}/{incr}:user/release-keys"

    if any(x in bl for x in ["xiaomi", "redmi", "poco"]):
        return f"Xiaomi/{device}/{device}:{android_ver}/{bid}/{inc}:user/release-keys"

    # Generic: brand/product/device:version/build/incremental:user/release-keys
    # Use uppercase for brand and lowercase for product path
    return f"{brand.upper()}/{device.lower()}/{device.lower()}:{android_ver}/{bid}/{inc}:user/release-keys"

def is_mobile_phone(name, model, device):
    # Skip if contains non-ASCII (Chinese/Japanese characters, etc.)
    if not all(ord(c) < 128 for c in name): return False
    
    name, mod, dev = name.lower(), model.lower(), device.lower()
    
    # Strict Excludes: TV, Tablets, Monitors, STB, etc.
    hard_excludes = [
        'chromebook', 'cheets', 'bravia', 'mitv', 'mi tv', 'android tv', 'google tv', 
        'laptop', 'tablet', 'watch', 'buds', 'earphone', 'monitor', 'display', 
        'panel', 'signage', 'stick', 'box', 'player', 'car', 'automotive',
        'projector', 'meeting', 'tv', 'uhd', 'led', 'lcd', 'oled', 'smart', 
        'commercial', 'signage', 'dtab', 'viera', 'aquos tv', 'stb', 'ott', 'dvb',
        'router', 'cpe', 'hotspot', 'modem', 'gateway', 'sketsa', 'tab', 'pad',
        'terminal', 'pos ', 'hub ', 'cast', 'bridge', 'vx_neo', 'vx lite', 'vane'
    ]
    if any(x in name or x in mod or x in dev for x in hard_excludes):
        return False

    # ZTE specific STB/Router patterns
    if mod.startswith('zxv') or mod.startswith('b86') or mod.startswith('zx'): return False

    # Check for commas (mostly TVs listing multiple sizes)
    if ',' in name or ',' in mod: return False
    
    # Carrier Bloat / Specific non-phone patterns
    if mod.startswith('d-') or mod.startswith('so-'): return False # Docomo/Sony Tablet
    if len(name) < 3: return False # Skip names like "A", "1"
    if name.isdigit(): return False # Skip pure numeric names

    # Samsung Tablet/Watch prefixes
    if re.search(r'^sm-[txpw][0-9]', mod): return False
    
    # Lenovo/Other Tablet patterns
    if re.search(r'\btab\b|\bpad\b', name): return False

    # Emulators / SDKs
    emu_keywords = ['emulator', 'generic', 'sdk built for', 'x86', 'vbox', 'vsoc', 'gphone', 'arm64', 'qemu']
    if any(x in name or x in mod or x in dev for x in emu_keywords):
        return False

    # Exclude very old devices / Legacy names
    legacy_names = ['nexus s', 'nexus 10', 'moment', 'behold', 'replenish', 'repp', 'sidekick', 'transform', 'vinsq']
    if any(x in name for x in legacy_names): return False
    
    # Xiaomi Legacy (HM = Hongmi/Redmi 1-4 era, MI 1-5 era)
    if re.search(r'^(hm|hongmi|mi 1|mi 2|mi 3|mi 4|mi 5)', mod): return False

    if re.search(r'^gt-i[0-9]{4}|^sch-r|^sph-m', mod): return False

    return True

def download_csv():
    print(f"[*] Downloading CSV from {CSV_URL}...")
    try:
        urllib.request.urlretrieve(CSV_URL, CSV_PATH)
        print("[+] Download complete.")
    except Exception as e:
        print(f"[!] Download failed: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="KuySpoof Database Generator")
    parser.add_argument("--update", action="store_true", help="Download latest CSV from Google")
    args = parser.parse_args()

    if args.update or not os.path.exists(CSV_PATH):
        download_csv()

    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)

    print("[*] Processing CSV...")
    results = {b["file"]: [] for b in TARGET_BRANDS}
    seen = set()

    # The CSV from Google is UTF-16LE
    try:
        with open(CSV_PATH, "r", encoding="utf-16") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand = row.get("Retail Branding", "").strip()
                model = row.get("Model", "").strip()
                device = row.get("Device", "").strip()
                mname = row.get("Marketing Name", "").strip()

                if not model or not device: continue
                if model in seen: continue
                
                # Check which target brand it belongs to
                target = None
                for b_cfg in TARGET_BRANDS:
                    # Specific rule for Google: only match Retail Branding
                    if b_cfg["file"] == "google":
                        if re.search(r"^google$", brand, re.IGNORECASE):
                            target = b_cfg["file"]
                            break
                        continue

                    # Other brands: check in Brand, Marketing Name, and Model
                    search_str = f"{brand} {mname} {model}"
                    if re.search(b_cfg["match"], search_str, re.IGNORECASE):
                        target = b_cfg["file"]
                        break
                
                if not target: continue
                if not is_mobile_phone(mname, model, device): continue

                # Technical Model vs Marketing Name
                if target in ["google", "nokia"]:
                    final_model = mname if mname else model
                else:
                    # For Motorola, we prefer XT codes if available, but model column is usually okay
                    final_model = model
                
                # Brand-specific filters for cleaner DB
                if target == "samsung" and not final_model.upper().startswith("SM-"):
                    continue
                if target == "sony" and not re.search(r"^(XQ-|SO-|SOG)", final_model, re.IGNORECASE):
                    continue
                # If it's a Lenovo-named device under Motorola branding, move it to Lenovo
                if target == "motorola" and final_model.lower().startswith("lenovo"):
                    target = "lenovo"
                
                # For Motorola, try to keep it to XT/Moto series for higher fidelity
                if target == "motorola" and not re.search(r'^(xt|moto|edge|razr|one )', final_model.lower()):
                    # If it's none of those, it might be a weird carrier name, keep if it looks like a model code
                    if len(final_model) < 4: continue

                # For ZTE, skip models that look like pure numbers or STB codes
                if target == "zte":
                    if final_model.isdigit() or len(final_model) < 4: continue
                    # Focus on known ZTE series if the model name is generic
                    if not re.search(r'(blade|axon|nubia|nubia|libero|voyager)', f"{mname} {final_model}".lower()):
                        if re.search(r'^(zx|b86|a[0-9]{3}|z[0-9]{3})', final_model.lower()): continue
                        if len(final_model) < 5: continue

                # Clean model name if it was a marketing name (Google, Nokia)
                if target in ["google", "nokia"]:
                    final_model = re.sub(r'\s*\([^)]*\)', '', final_model)
                    final_model = final_model.split('/')[0].split('|')[0].strip()

                # Check for duplicates per brand + model + device
                seen_key = f"{target}_{final_model}_{device}"
                if seen_key in seen: continue
                seen.add(seen_key)

                ver = get_android_version(brand, model, device)
                finger = get_fingerprint(brand, model, device, ver)

                results[target].append({
                    "model": final_model,
                    "device": device,
                    "fingerprint": finger
                })
    except Exception as e:
        print(f"[!] Error reading CSV: {e}")
        return

    # Save to JSON
    for brand_file, items in results.items():
        if not items:
            print(f"[-] Skip {brand_file} (no devices)")
            continue
        
        items.sort(key=lambda x: x["model"])
        out_path = os.path.join(DB_PATH, f"{brand_file}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)
        print(f"[+] Generated {out_path} ({len(items)} devices)")

    print("[*] All done!")

if __name__ == "__main__":
    main()
