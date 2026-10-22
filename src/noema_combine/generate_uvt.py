# import os
from typing import TextIO, List, Dict, Any
import yaml
from datetime import datetime


def make_header(file: TextIO) -> None:
    header = datetime.today().strftime("%Y-%m-%d")
    file.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    file.write("!\n")
    file.write("!  Generate LR + HR chunk UVT files \n")
    file.write("!\n")
    file.write("!  Created for MIOP L19MB project\n")
    file.write(f"!  generate_miop_uvt, {header}\n")
    file.write("!\n")
    file.write("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
    file.write("def integer new_file /global\n")
    file.write("let new_file 1\n")
    file.write("!\n")
    return


def make_uvt_names(sources: list[str], config: str) -> list[str]:
    # check that sources contains exactly two elements and that they are strings
    if len(sources) != 2:
        raise ValueError("Sources list must contain exactly two elements.")

    uvt_out = [
        f"../../uvts/{sources[0]}/{config}config/{sources[0]}_{config}",
        f"../../uvts/{sources[1]}/{config}config/{sources[1]}_{config}",
    ]
    return uvt_out


def print_makespw(file: TextIO, uvt_out: list[str], sources: list[str]) -> None:
    # check that sources contains exactly two elements and that they are strings
    if len(sources) != 2:
        raise ValueError("Sources list must contain exactly two elements.")
    file.write("!\n")
    file.write(f"! Make uv-tables for sources: {sources[0]} and {sources[1]}\n")
    file.write("! ! &1 = output table name parameter\n")
    file.write("!\n")
    file.write("! This procedure makes either make a new uvt\n")
    file.write("! or append to a uvt, depending on the value of new_file\n")
    file.write("!\n")
    # This procedure makes a new uvt
    file.write("begin procedure makespw\n")
    file.write("  if (new_file.eq.1) then\n")
    file.write(f"    find /proc corr /sou {sources[0]}\n")
    file.write(f'    table "{uvt_out[0]}_&1" new\n')
    file.write(f"    find /proc corr /sou {sources[1]}\n")
    file.write(f'    table "{uvt_out[1]}_&1" new\n')
    file.write("  else\n")
    file.write(f"    find /proc corr /sou {sources[0]}\n")
    file.write(f'    table "{uvt_out[0]}_&1"\n')
    file.write(f"    find /proc corr /sou {sources[1]}\n")
    file.write(f'    table "{uvt_out[1]}_&1"\n')
    file.write("  endif\n")
    file.write("end procedure makespw\n")
    file.write("!\n")
    return


def calibration_type(
    file: TextIO,
    receiver: str,
    file_name: str,
    phase_cal: str,
    amp_cal: str,
    RF_cal: str,
) -> None:
    file.write("!\n")
    file.write("set default\n")
    file.write("set scan 0 10000\n")
    file.write("set offset 0 0\n")
    file.write(f"set receiver {receiver}\n")
    file.write("set quality average\n")
    file.write("set weight tsys on\n")
    file.write("set weight calibration on\n")
    if phase_cal == "antenna":
        file.write("set phase antenna atmospher internal relative\n")
    else:
        print("Phase calibration requested as baseline, but not available")
        file.write("set phase antenna atmospher internal relative\n")
    if amp_cal == "antenna":
        file.write("set amplitude antenna absolute jansky relative\n")
    else:
        file.write("set amplitude baseline relative\n")
    if RF_cal == "antenna":
        file.write("set rf_passband antenna spectrum file 1 on\n")
    else:
        file.write("set rf_passband antenna spectrum file 1 on\n")
        file.write("set rf baseline on\n")
        file.write("set amplitude baseline relative\n")
    file.write("set drop 0.00000001 0.00000001\n")
    file.write("!\n")
    file.write(f'file in "{file_name}"\n')
    return


def look_spw(file: TextIO, high_res_parameters: Dict[str, int]) -> None:
    # Get parameters with defaults from clic configuration file if not provided
    number_windows = high_res_parameters.get("number_windows", 38)
    LI_start = high_res_parameters.get("LI_start", 23)
    UI_start = high_res_parameters.get("UI_start", 32)
    UO_start = high_res_parameters.get("UO_start", 40)
    sb = "lsb"
    file.write("!\n")
    file.write("begin procedure loopspw\n")
    file.write("!  These define the chunks used to make each spw\n")
    file.write("!\n")
    file.write("!!!!!!!!! Wideband chunks\n")
    file.write("!\n")
    file.write("  set selection line lsb l001 and l005 \n")
    file.write("  @ makespw lo\n")
    file.write("  !\n")
    file.write("  set selection line lsb l002 and l006 \n")
    file.write("  @ makespw li\n")
    file.write("  !\n")
    file.write("  !\n")
    file.write("  set selection line usb l003 and l007 \n")
    file.write("  @ makespw ui\n")
    file.write("  !\n")
    file.write("  set selection line usb l004 and l008 \n")
    file.write("  @ makespw uo\n")
    file.write("  !\n")
    file.write("  !!!!!!!!! LO chunks\n")
    file.write("  !\n")
    for i in range(9, number_windows + 9 + 1):
        if i == LI_start:
            file.write("  !\n")
            file.write("  !!!!!!!!! LI chunks\n")
            file.write("  !\n")
        elif i == UI_start:
            sb = "usb"
            file.write("  !\n")
            file.write("  !!!!!!!!! UI chunks\n")
            file.write("  !\n")
        elif i == UO_start:
            file.write("  !\n")
            file.write("  !!!!!!!!! UO chunks\n")
            file.write("  !\n")
        file.write(
            f"  set selection line {sb} l{i:03} and l{i + number_windows + 1:03} \n"
        )
        file.write(f"  @ makespw l{i:03}l{i + number_windows + 1:03} \n")
        file.write("  !\n")
    file.write("end procedure loopspw\n")
    return


def prepare_config(
    setup_name: str,
    sources: list[str],
    receiver: str,
    hpb_dict: List[Dict[str, Any]],
    high_res_parameters: Dict[str, int],
    config: str = "C",
) -> None:
    #
    print(f"Creating {config} configuration CLIC file for {setup_name}")
    file_out = open(f"{setup_name}-{config}-uvts.clic", "w")
    make_header(file_out)
    uvt_names = make_uvt_names(sources, config)
    print_makespw(file_out, uvt_names, sources)
    look_spw(file_out, high_res_parameters)
    for i, entry in enumerate(hpb_dict):
        file_name = entry.get("file", None)
        if file_name is None:
            print(f"Warning: No file specified in entry {i}. Skipping.")
            continue
        phase_cal = entry.get("phase calibration type", "antenna")
        amp_cal = entry.get("amplitude calibration type", "antenna")
        RF_cal = entry.get("RF calibration type", "antenna")

        calibration_type(file_out, receiver, file_name, phase_cal, amp_cal, RF_cal)
        file_out.write("@ loopspw\n")
        if i == 0:
            file_out.write("!\n!reuse the previous file\nlet new_file 0\n!\n")
        print(
            f"File: {file_name}, Phase Calibration: {phase_cal}, Amplitude Calibration: {amp_cal}, RF Calibration: {RF_cal}"
        )
    return


def process_source(setup_name: str, config_path: str = "clic_config_MIOP.yaml") -> None:
    # Load configuration from YAML file
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    # NOEMA Band 1 (3mm), Band 2 (2mm), Band 3 (1mm)
    receiver = config.get("receiver", 3)
    print(f"Using receiver: {receiver}")

    setups = config.get("setups", {})
    setup = setups.get(setup_name, None)
    if not setup:
        print(f"No configuration found for setup: {setup_name}")
        return
    high_res_parameters = config.get("highres_parameters", {})
    sources = setup.get("sources", [])
    Afiles = setup.get("A-files", [])
    Bfiles = setup.get("B-files", [])
    Cfiles = setup.get("C-files", [])
    Dfiles = setup.get("D-files", [])
    do_Aconf = len(Afiles) > 0
    do_Bconf = len(Bfiles) > 0
    do_Cconf = len(Cfiles) > 0
    do_Dconf = len(Dfiles) > 0
    #
    # open an ascii file for writeout
    # Create CLIC files for C, D, CD, and ACD configurations
    #
    if do_Aconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Afiles,
            config="A",
            high_res_parameters=high_res_parameters,
        )
    if do_Bconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Bfiles,
            config="B",
            high_res_parameters=high_res_parameters,
        )

    if do_Cconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Cfiles,
            config="C",
            high_res_parameters=high_res_parameters,
        )

    if do_Dconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Dfiles,
            config="D",
            high_res_parameters=high_res_parameters,
        )
    # now combine configurations if more than one is present
    if do_Cconf and do_Dconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Cfiles + Dfiles,
            config="CD",
            high_res_parameters=high_res_parameters,
        )

    if do_Bconf and do_Cconf and do_Dconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Bfiles + Cfiles + Dfiles,
            config="BCD",
            high_res_parameters=high_res_parameters,
        )

    if do_Aconf and do_Cconf and do_Dconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Cfiles + Dfiles + Afiles,
            config="ACD",
            high_res_parameters=high_res_parameters,
        )

    if do_Aconf and do_Bconf and do_Cconf and do_Dconf:
        prepare_config(
            setup_name=setup_name,
            sources=sources,
            receiver=receiver,
            hpb_dict=Afiles + Bfiles + Cfiles + Dfiles,
            config="ABCD",
            high_res_parameters=high_res_parameters,
        )

    return
