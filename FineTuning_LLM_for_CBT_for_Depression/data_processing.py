import os
import re
import pandas as pd

# -----------------------------
# CONFIGURATION
# -----------------------------
root_folder = "Qwen_Finetune_Simulation_Nov_16"
output_root = "parsed_output"

# Make the root output folder
os.makedirs(output_root, exist_ok=True)

# Regex to detect speakers
therapist_re = re.compile(r"^Therapist:\s*(.*)", re.IGNORECASE)
patient_re = re.compile(r"^Patient:\s*(.*)", re.IGNORECASE)


def parse_session(filepath):
    """
    Parse a single .txt file into paired Therapist–Patient turns.
    Handles multi-paragraph turns and continuation lines.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    conversation = []
    current_speaker = None
    buffer = ""

    def push(role, text):
        if text.strip():
            conversation.append((role, text.strip()))

    # Process each line
    for line in lines:
        t = therapist_re.match(line)
        p = patient_re.match(line)

        if t:
            if buffer:
                push(current_speaker, buffer)
            current_speaker = "Therapist"
            buffer = t.group(1).strip()

        elif p:
            if buffer:
                push(current_speaker, buffer)
            current_speaker = "Patient"
            buffer = p.group(1).strip()

        else:
            buffer += " " + line.strip()

    # Push last turn
    if buffer:
        push(current_speaker, buffer)

    # Pair the turns
    pairs = []
    last_therapist = None

    for speaker, text in conversation:
        if speaker == "Therapist":
            last_therapist = text
        else:  # Patient
            if last_therapist:
                pairs.append([last_therapist, text])
                last_therapist = None
            else:
                pairs.append(["", text])

    return pd.DataFrame(pairs, columns=["Therapist", "Patient"])


# -----------------------------
# MAIN: PROCESS ALL PATIENT FOLDERS
# -----------------------------
for patient_folder in os.listdir(root_folder):
    patient_path = os.path.join(root_folder, patient_folder)

    if not os.path.isdir(patient_path):
        continue

    print(f"Processing: {patient_folder}")

    # Extract patient name: everything after the last underscore
    # Example: "CBT_Depression_Simulation_Derek Olsen" → "Derek Olsen"
    parts = patient_folder.split("_")
    patient_name = " ".join(parts[3:])   # join all remaining words after Simulation

    # Create matching output folder
    patient_outdir = os.path.join(output_root, patient_folder)
    os.makedirs(patient_outdir, exist_ok=True)

    # Loop over session files
    for fname in os.listdir(patient_path):
        if fname.endswith(".txt") and fname.startswith("session_"):
            session_in_path = os.path.join(patient_path, fname)

            # Extract session number (session_9_xyz → "9")
            session_number = fname.split("_")[1]

            df = parse_session(session_in_path)

            # Add metadata columns
            df.insert(0, "patient_name", patient_name)
            df.insert(1, "session_number", session_number)

            # Save CSV
            session_base = os.path.splitext(fname)[0]
            out_path = os.path.join(patient_outdir, f"{session_base}.csv")

            df.to_csv(out_path, index=False, encoding="utf-8")
            print(f"Saved: {out_path}")

print("\nAll sessions processed successfully!")
