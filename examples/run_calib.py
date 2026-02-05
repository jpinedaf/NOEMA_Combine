import noema_combine

# L09
# mol = 'DCO+'
# QN = '1-0'
# mol = 'CCD'
# QN = "N=1-0,J=3/2-1/2,F=5/2-3/2"

# L10
# mol = 'DCN'
# QN = '1-0'
# mol = 'H2CO'
# QN = "5(1,4)-5(1,5)"

# L11
# mol = 'SO2'
# QN = "6(0,6)-5(1,5)"
# mol = 'HC3N'
# QN = "8-7"
# mol = 'H2CO'
# QN = "1(0,1)-0(0,0)"

# L15
# mol = 'C4H'
# QN = "N=8-7,J=17/2-15/2,F=8-7"
# mol = 'C4H'
# QN = "N=8-7,J=15/2-13/2,F=7-6"
# mol = 'DNC'
# QN = "1-0"
# mol = 'CH3OH'
# QN = "5(0,5)-4(-1,3)E,vt=0"

# L16
mol = "N2D+"
QN = "1-0"

# L17
# mol = 'H13CO+'
# QN = '1-0'


# L18
# mol = 'CCH'
# QN = "N=1-0,J=3/2-1/2,F=2-1" # not covered by 30m
# QN = "N=1-0,J=3/2-1/2,F=1-1" # not covered by 30m
# QN = "N=1-0,J=3/2-1/2,F=1-0" # not covered by 30m

# L19
# mol = 'CCH'
# QN = "N=1-0,J=1/2-1/2,F=2-1" # not covered by 30m
# QN = "N=1-0,J=1/2-1/2,F=1-1" # not covered by 30m
# QN = "N=1-0,J=1/2-1/2,F=1-0" # not covered by 30m

# L20
# mol = 'HNCO' # not covered by 30m
# QN = None

# L21
# mol = 'HCN'
# QN = '1-0'

# L22
# mol = 'HCO+'
# QN = '1-0'

# L23
# mol = 'HNC'
# QN = '1-0'
# mol = 'CCS'
# QN = 'N=7-6,J=7-6'

# L24
# mol = 'HC3N'
# QN = '10-9'

# L27
# mol = '13CS'
# QN = '2-1'

# L28
# mol = 'N2H+'
# QN = '1-0'

# L29
# mol = 'CCS'
# QN = 'N=7-6,J=8-7'

# noema_combine.data_handler.line_make_uvt('B5', mol, QN)
# noema_combine.data_handler.line_reduce_sd('B5', mol, QN)  # use line_reduce_sd instead of line_reduce_30m
noema_combine.data_handler.line_prepare_merge("B5", mol, QN)

# noema_combine.data_handler.line_reduce_sd('B5', 'HCNH+', QN)  # use line_reduce_sd instead of line_reduce_30m
