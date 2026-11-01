from noema_combine.merge import build_uv_merge_init, build_uv_merge_script
from noema_combine.uvfits import build_uvfits_export_script


def test_uv_merge_scripts_define_inputs_and_output():
    init = build_uv_merge_init("a.uvt", "b.uvt", "merged.uvt")
    assert 'TABLE_IN$ "a.uvt"' in init
    assert 'TABLE_REF$ "b.uvt"' in init
    assert 'TABLE_OUT$ "merged.uvt"' in init
    assert "run uv_merge uv_merge.init /nowindow" in build_uv_merge_script()


def test_uvfits_export_script_quotes_paths():
    script = build_uvfits_export_script("input.uvt", "output.uvfits")
    assert 'fits "output.uvfits" from "input.uvt" /style CASA_UVFITS /overwrite' in script
