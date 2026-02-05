import tempfile
import os
from glob import glob
import numpy as np
from numpy.typing import NDArray
import warnings
from astropy.coordinates import SkyCoord  # type: ignore
import astropy.units as u  # type: ignore

# Import configuration
from .config import get_config

# Initialize configuration (loaded once)
_cfg = get_config()

# Create module-level aliases for backward compatibility
file_source_catalogue = _cfg.file_source_catalogue
region_catalogue = _cfg.region_catalogue
selfcal_ext = _cfg.selfcal_ext
uvsub_ext = _cfg.uvsub_ext
file_line_catalogue = _cfg.file_line_catalogue
file_extensions_sd = _cfg.file_extensions_sd
telescope_class = _cfg.telescope_class
ignorefiles = _cfg.ignorefiles
line_name = _cfg.line_name
qn = _cfg.qn
freq = _cfg.freq
name_str = _cfg.name_str
qn_str = _cfg.qn_str
Lid = _cfg.Lid
vel_width = _cfg.vel_width
vel_width_sd = _cfg.vel_width_sd
vel_width_base_sd = _cfg.vel_width_base_sd
uvt_dir = _cfg.uvt_dir
dir_sd = _cfg.dir_sd  # Uses config with automatic deprecation warning for dir_30m
uvt_dir_out = _cfg.uvt_dir_out
inputdir = _cfg.inputdir

# Type hints for data arrays
list_source_name: NDArray[np.str_]
list_source_key: NDArray[np.str_]
list_source_out: NDArray[np.str_]
list_RA: NDArray[np.str_]
list_Dec: NDArray[np.str_]
list_Vlsr: NDArray[np.str_]


def get_line_param(line_name_i: str, qn_i: str | None) -> int:
    """
    Function to find the index of the line in the catalogue.
    If the Quantum number is not given, it will return the line only if there is a single entry in the catalogue.
    In the case of multiple line entried for the same molecule, an error is raised.
    """
    if qn_i is None:
        idx = np.where(line_name == line_name_i)[0]
        if len(idx) > 1:
            raise ValueError(
                f"Line name is not unique: {line_name_i}, add the Quantum number (qn)."
            )
    else:
        print(f"line_name: {line_name_i}, qn: {qn_i}")
        idx = np.where((line_name == line_name_i) & (qn_str == qn_i))[0]
    if len(idx) == 0:
        raise ValueError(f"Line not found in the catalogue: {line_name_i}")
    return int(idx[0])


def get_source_param(source_name: str) -> tuple[str, str, str, float, float, float]:
    """
    Function to reach the source in the catalogue.
    It returns the values in the catalogue for the source.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5-IRS1"
    returns:
    --------
    source_name: str
        Name of the source to reduce, e.g., "B5-IRS1"
    source_sd: str
        Name of the source in the single dish (30m) observations, e.g., "B5", or "B5-Box1 B5-Box2"
    source_out: str
        Name of the source for the output files, e.g., "B5"
    ra0: float
        Right Ascension of the source in degrees.
    dec0: float
        Declination of the source in degrees.
    vlsr: float
        LSR velocity of the source in km/s.
    """
    print(f"source_name: {source_name}")
    try:
        region_catalogue[source_name]
    except KeyError:
        raise ValueError(f"Region '{source_name}' not found in region_catalogue")

    if (":" in region_catalogue[source_name]["RA0"]) and (
        ":" in region_catalogue[source_name]["Dec0"]
    ):
        skycoord: SkyCoord = SkyCoord(
            region_catalogue[source_name]["RA0"]
            + " "
            + region_catalogue[source_name]["Dec0"],
            frame="icrs",
            unit=(u.hourangle, u.deg),  # type: ignore
        )
    elif ("h" in region_catalogue[source_name]["RA0"]) and (
        "d" in region_catalogue[source_name]["Dec0"]
    ):
        skycoord: SkyCoord = SkyCoord(
            ra=region_catalogue[source_name]["RA0"],
            dec=region_catalogue[source_name]["Dec0"],
            frame="icrs",
        )
    else:
        skycoord: SkyCoord = SkyCoord(
            ra=float(region_catalogue[source_name]["RA0"]),
            dec=float(region_catalogue[source_name]["Dec0"]),
            frame="icrs",
            unit=(u.deg, u.deg),  # type: ignore
        )
    ra_cat: float = skycoord.ra.degree  # type: ignore
    dec_cat: float = skycoord.dec.degree  # type: ignore
    return (
        source_name,
        region_catalogue[source_name]["source_sd"],
        region_catalogue[source_name]["source_out"],
        ra_cat,
        dec_cat,
        float(region_catalogue[source_name]["Vlsr"]),
    )


def get_uvt_window(
    source_name: str, Lid: str, uvsub: bool = True, selfcal: bool = False
) -> str:
    """
    Function to generate the output file name for NOEMA uvt file.
    The file will be in the uvt_dir folder.
    The format will be:
    {uvt_dir}/{Lid}/{source_name}_{Lid}(extension).uvt
    where (extension) depends on the uvsub and selfcal parameters.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    Lid: str
        Window unit for the NOEMA data, e.g., "L09", "l11", depending on the specification from the line catalogue.
    uvsub: bool
        If True, the file will include '_uvsub' in the name.
    selfcal: bool
        If True, the file will include '_sc' in the name.
    """
    extension = ""
    if selfcal:
        extension += selfcal_ext
    if uvsub:
        extension += uvsub_ext
    uvt_filename = os.path.join(uvt_dir, Lid, f"{source_name}_{Lid}{extension}.uvt")
    return uvt_filename


def get_uvt_file(
    source_name: str, line_name: str, qn: str, Lid: str, merge: bool = False
) -> str:
    """
    Function to generate the output file name for NOEMA uvt file.
    The format will be:
    {dir_out}/{source_name}_{line_name}_{qn}_{Lid}.uvt
    where {dir_out} depends on the merge parameter.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_name: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    Lid: str
        Window unit for the NOEMA data, e.g., "L09", "l11", depending on the specification from the line catalogue.
    merge: bool
        If True, the file will be saved in the merge folder, otherwise in the uvt folder.
    """
    if not merge:
        dir_out = uvt_dir
    else:
        dir_out = uvt_dir_out
    uvt_filename = os.path.join(
        dir_out, Lid, f"{source_name}_{line_name}_{qn}_{Lid}.uvt"
    )
    return uvt_filename


def get_30m_file(
    source_name: str, line_name: str, qn: str, Lid: str, merge: bool = False
) -> str:
    """
    Function to generate the output file name for the single dish data.
    The format will be:
    {dir_sd}{source_out}_{line_name}_{qn}.{file_extensions_sd}
    of
    {dir_sd}{source_out}_{line_name}_{qn}_{Lid}.{file_extensions_sd}
    depending on the merge parameter.

    .. deprecated::
        This function is deprecated and will be removed in a future version.
        Use `get_sd_file()` instead, which supports all single dish telescopes
        (IRAM 30m, APEX, etc.) through the `telescope_sd` configuration.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_name: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    Lid: str
        Window unit for the NOEMA data, e.g., "L09", "l11", depending on the specification from the line catalogue.
    merge: bool
        If True, the file will include the Lid information in the name.
    """
    warnings.warn(
        "get_30m_file() is deprecated and will be removed in a future version. "
        "Use get_sd_file() instead, which supports all single dish telescopes.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_sd_file(source_name, line_name, qn, Lid, merge=merge)


def get_sd_file(
    source_name: str, line_name: str, qn: str, Lid: str, merge: bool = False
) -> str:
    """
    Function to generate the output file name for single dish data.
    Supports all single dish telescopes (IRAM 30m, APEX, etc.) as configured
    in the `telescope_sd` setting.

    The file format will be:
    {dir_sd}{source_out}_{line_name}_{qn}.{file_extensions_sd}
    or
    {dir_sd}{source_out}_{line_name}_{qn}_{Lid}.{file_extensions_sd}
    depending on the merge parameter.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_name: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    Lid: str
        Window unit for the NOEMA data, e.g., "L09", "l11", depending on the specification from the line catalogue.
    merge: bool
        If True, the file will include the Lid information in the name.
    """
    if merge:
        name_out = f"{source_name}_{line_name}_{qn}_{Lid}{file_extensions_sd}"
    else:
        name_out = f"{source_name}_{line_name}_{qn}{file_extensions_sd}"
    outputfile = os.path.join(dir_sd, name_out)
    return outputfile


def line_prepare_merge(source_name: str, line_i: str, qn_i: str) -> None:
    """
    Function to prepare the single dish (30m) data for the merging.
    It will ensure that the single dish (30m) data are in Tmb and in the correct frequency.
    It will use the uvt file from the NOEMA observations to regrid the
    speactral axis of the single dish (30m) data.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    """
    _, _, source_out, _, _, _ = get_source_param(source_name)

    print(f"[INFO] Reducing line: {line_i} with qn: {qn_i}")
    index = get_line_param(line_i, qn_i)
    qn_name_i = qn[index]
    line_name_i = line_name[index]
    freq_i = freq[index].astype(float) * 1e3
    Lid_i = Lid[index]
    file_uvt = get_uvt_file(source_out, line_name_i, qn_name_i, Lid_i, merge=False)
    merge_uvt = get_uvt_file(source_out, line_name_i, qn_name_i, Lid_i, merge=True)

    file_sd = get_sd_file(source_out, line_name_i, qn_name_i, Lid_i, merge=False)
    merge_sd = get_sd_file(source_out, line_name_i, qn_name_i, Lid_i, merge=True)

    os.system(f"rm {os.path.splitext(merge_sd)[0]}.*")
    fb = tempfile.NamedTemporaryFile(delete=True, mode="w+", dir=".", suffix=".class")
    fb.write(f'file in "{file_sd}"\n')
    fb.write(f'file out "{merge_sd}"  single /overwrite\n')
    fb.write("say [INFO] Removing old output file\n")
    fb.write(f'say "[INFO] Making new output file: {merge_sd}"\n')
    fb.write("find\n")
    fb.write("set mode x auto\n")
    fb.write("set unit v f\n")
    fb.write("get zero\n")
    fb.write("sic message class s-i\n")
    fb.write("for i 1 to found\n")
    fb.write("  get next\n")
    fb.write(f"  modify linename {name_str[index]}\n")
    fb.write(f"  modify freq {freq_i}\n")
    fb.write(f"  modify source {source_out}\n")
    fb.write("  modify Beam_Eff /Ruze\n")
    fb.write("  write\n")
    fb.write("next\n")
    fb.write("sic message class s+i\n")
    fb.write(f'file in "{merge_sd}"\n')
    fb.write("find /all\n")
    fb.write("if found.eq.0 exit\n")
    fb.write(
        f'table "{os.path.splitext(merge_uvt)[0]}" new /NOCHECK source /like "{file_uvt}"\n'
    )
    fb.write("exit\n")
    fb.flush()
    merged_folder = os.path.dirname(merge_uvt)  # get path only
    if not os.path.exists(merged_folder):
        os.makedirs(merged_folder)

    # copy to folder for merging
    # os.system("cp {0}.tab {1}/.".format(outputfile, merged_folder))
    os.system(f"class -nw @ {fb.name}")
    fb.close()
    os.system(f"cp {file_uvt} {merged_folder}/.")


def line_reduce_30m(source_name: str, line_i: str, qn_i: str) -> None:
    """
    Function to perform a simple data reduction ot the 30m data.
    Output spectra will be stores in Ta* scale.
    It will ensure that the 30m data use the correct frequency and coordinate center.

    .. deprecated::
        This function is deprecated and will be removed in a future version.
        Use `line_reduce_sd()` instead, which supports all single dish telescopes
        (IRAM 30m, APEX, etc.) through the `telescope_sd` configuration.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_i: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn_i: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    """
    warnings.warn(
        "line_reduce_30m() is deprecated and will be removed in a future version. "
        "Use line_reduce_sd() instead, which supports all single dish telescopes.",
        DeprecationWarning,
        stacklevel=2,
    )
    line_reduce_sd(source_name, line_i, qn_i)


def line_reduce_sd(source_name: str, line_i: str, qn_i: str) -> None:
    """
    Function to perform simple data reduction on single dish data.
    Supports all single dish telescopes (IRAM 30m, APEX, etc.) as configured
    in the `telescope_sd` setting.

    Output spectra will be stored in Ta* scale.
    It will ensure that the single dish data use the correct frequency and coordinate center.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_i: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn_i: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    """
    _, source_find, source_out, ra0, dec0, vlsr = get_source_param(source_name)

    freq_corr = 1 - vlsr / 3e5
    # Get data files list from all input directories
    inputfiles: list[str] = []
    for input_dir in inputdir:
        # Use glob to find all single dish files in each directory
        files_in_dir = glob(os.path.join(input_dir, f"*{file_extensions_sd}"))
        inputfiles.extend(files_in_dir)
    if len(inputfiles) == 0:
        raise ValueError(f"No files found in the input directory: {inputdir}")

    print(f"[INFO] Found {len(inputfiles)} files in input directories")
    print(f"[INFO] Reducing line: {line_i} with qn: {qn_i}")
    index = get_line_param(line_i, qn_i)
    print(source_out, line_name[index], qn[index])
    # Get frequency
    Lid_i = Lid[index]
    qn_name_i = qn[index]
    line_name_i = line_name[index]
    freq_i = freq[index].astype(float) * 1e3
    dv_base = vel_width_base_sd[index].astype(float)
    dv = vel_width_sd[index].astype(float)
    print(vlsr + 0.1, dv + 0.1, dv_base + 0.1)
    vel_win = "{0:.2f}  {1:.2f}".format(vlsr - dv_base, vlsr + dv_base)
    vel_ext = "{0:.2f}  {1:.2f}".format(vlsr - dv, vlsr + dv)
    # Define output
    file_sd = get_sd_file(source_out, line_name_i, qn_name_i, Lid_i, merge=False)
    os.system(f"rm {os.path.splitext(file_sd)[0]}.*")
    fb = tempfile.NamedTemporaryFile(delete=True, mode="w+", dir=".", suffix=".class")
    fb.write(f"file out {file_sd}  single\n")
    fb.write("say [INFO] Removing old output file\n")
    fb.write(f'say "[INFO] Making new output file: {file_sd}"\n')
    ####
    # Loop through files - one file per date
    for inputfile in inputfiles:
        # inputfile = os.path.join(inputdir, input_filename)
        # check everyfile to be ignored if it is the current file
        for ignorefile in ignorefiles:
            if ignorefile in inputfile:
                fb.write(f'say "[INFO] Ignoring file: {inputfile}"\n')
                continue
        fb.write(f'say "[INFO] Processing file: {inputfile}"\n')
        # Load file and det defaults
        fb.write(f'file in "{inputfile}"\n')
        fb.write(f"set source {source_find}\n")
        fb.write("set offset 0 0\n")
        fb.write("set angle sec\n")
        fb.write("set match 500\n")
        fb.write("set tele *\n")
        fb.write("set line *\n")
        # Open and check file
        # only observations with reference frequency
        fb.write("find /frequency {0}\n".format(freq_i * freq_corr))
        fb.write("set mode x auto\n")
        fb.write("set unit v\n")
        fb.write("get zero\n")
        fb.write("sic message class s-i\n")
        fb.write("for i 1 to found\n")
        fb.write("  get next\n")
        fb.write(f"  modify linename {name_str[index]}\n")
        fb.write(f"  modify freq {freq_i}\n")
        fb.write(f"  modify source {source_out}\n")
        # RA and Dec centers are in hrs and degrees, respectively
        fb.write(f"  modify projection = {ra0/15.0} {dec0} =\n")
        fb.write(f"  modify telescope {telescope_class}\n")
        fb.write(f"  extract {vel_ext} velocity\n")  # cut out spectra
        fb.write(f"  set window {vel_win}\n")  # define baseline window
        fb.write("  base 1\n")  # first order baseline
        fb.write("  write\n")
        fb.write("next\n")
        # ! Toggle back screen informational messages
        fb.write("sic message class s+i\n")
        # back to not setting up the source
        fb.write("set source\n")
    # Now process the whole dataset available
    # Regrid and output to fits file
    print(file_sd)
    fb.write(f"file in {file_sd}\n")
    fb.write("find /all\n")
    fb.write("if found.eq.0 exit\n")
    fb.write(f"table {os.path.splitext(file_sd)[0]} new /nocheck\n")
    fb.write(f"xy_map {os.path.splitext(file_sd)[0]}\n")
    fb.write("exit\n")
    fb.flush()
    os.system(f"rm -f {file_sd}")
    os.system(f"class -nw @ {fb.name}")
    fb.close()


def line_make_uvt(
    source_name: str,
    line_i: str,
    qn_i: str,
    uvsub: bool = True,
    selfcal: bool = False,
    dv: float | None = None,
    dv_min: float | None = None,
    dv_max: float | None = None,
) -> None:
    """
    Function to perform an exision of a targeted molecular line, from NOEMA data already calibrated.
    It will ensure that the Single Dish (30m) data use the correct frequency.
    The velocity range will be defined by the vlsr and the velocity width from the line catalogue, unless explicity requested using an ad-hoc dv value or direcly providing [vmin, vmax] parameters.

    parameters:
    -----------
    source_name: str
        Name of the source to reduce, e.g., "B5"
    line_i: str
        Molecule to reduce, e.g., "CO", "13CO", "N2H+"
    qn_i: str
        Quantum numbers of the line to reduce, e.g., "1-0" or "N=1-0,J=3/2-1/2,F=1/2-1/2"
    uvsub: bool
        If True, the file will include '_uvsub' in the name.
    selfcal: bool
        If True, the file will include '_sc' in the name.
    dv: float
        Velocity width to use for the extraction, [vlsr - dv, vlsr + dv] in km/s, this superseeds the value from the line catalogue.
    dv_min: float
        Minimum velocity difference with respect to vlsr to use for the extraction in km/s. Used only if dv is not defined and if vmax is also provided.
    dv_max: float
        Maximum velocity difference with respect to vlsr to use for the extraction in km/s. Used only if dv is not defined and if vmax is also provided.
    """
    _, _, source_out, _, _, vlsr = get_source_param(source_name)

    print(f"[INFO] Reducing line: {line_i} with qn: {qn_i}")
    index = get_line_param(line_i, qn_i)
    print(source_out, line_name[index], qn[index])
    # Get frequency
    Lid_i = Lid[index]
    qn_name_i = qn[index]
    line_name_i = line_name[index]
    freq_i = freq[index].astype(float) * 1e3
    if dv is not None:
        dv_window = dv
    else:
        dv_window = vel_width[index].astype(float)
    #
    window_uvt = get_uvt_window(source_out, Lid_i, uvsub=uvsub, selfcal=selfcal)
    file_uvt = get_uvt_file(source_out, line_name_i, qn_name_i, Lid_i, merge=False)
    if dv is None and dv_min is not None and dv_max is not None:
        vel_win = "{0:.2f}  {1:.2f}".format(vlsr - dv_min, vlsr + dv_max)
    else:
        vel_win = "{0:.2f}  {1:.2f}".format(vlsr - dv_window, vlsr + dv_window)
    # remove previous version of the file
    os.system(f"rm {os.path.splitext(file_uvt)[0]}.*")
    fb = tempfile.NamedTemporaryFile(delete=True, mode="w+", dir=".", suffix=".map")
    fb.write(f'modify "{window_uvt}" /frequency {name_str[index]} {freq_i}\n')
    fb.write(f'let name "{os.path.splitext(window_uvt)[0]}"\n')
    fb.write("let type uvt\n")
    fb.write("go setup\n")
    fb.write(f"uv_extract /range {vel_win} velocity\n")
    fb.write(f'write uv "{file_uvt}" new\n')
    fb.write("sic message mapping s-i\n")
    fb.write("sic message mapping s+i\n")
    fb.write("exit\n")
    fb.flush()
    os.system(f"mapping -nw @ {fb.name}")
    fb.close()
