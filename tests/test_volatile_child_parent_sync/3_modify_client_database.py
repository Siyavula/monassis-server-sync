{
    'records': [
        {'id': 1, 'column1': 'aa', 'column2': 'a', 'column3': 'a'},     # ii0, volatile: u1
        #{'id': 2, 'column1': 'bb', 'column2': 'bb', 'column3': 'bb'},  # ii0, volatile: d
        {'id': 3, 'column1': 'cc', 'column2': 'cc', 'column3': 'cc'},   # ii1, volatile: u0
        {'id': 4, 'column1': 'dd', 'column2': 'dd', 'column3': 'dd'},   # ii1, volatile: u1
        #{'id': 5, 'column1': 'ee', 'column2': 'ee', 'column3': 'ee'},  # ii1, volatile: d
        {'id': 6, 'column1': 'ff', 'column2': 'ff', 'column3': 'ff'},   # i-,  volatile: u1
        #{'id': 7, 'column1': 'gg', 'column2': 'gg', 'column3': 'gg'},  # i-,  volatile: d
        {'id': 8, 'column1': 'hh', 'column2': 'hh', 'column3': 'hh'},   # -i,  volatile: i0
        {'id': 9, 'column1': 'ii', 'column2': 'i', 'column3': 'i'},     # -i,  volatile: i1
        {'id': 10, 'column1': 'jj', 'column2': 'jj', 'column3': 'j'},   # uu0, volatile: u1
        #{'id': 11, 'column1': 'kk', 'column2': 'kk', 'column3': 'kk'}, # uu0, volatile: d
        {'id': 12, 'column1': 'll', 'column2': 'll', 'column3': 'll'},  # uu1, volatile: u0
        {'id': 13, 'column1': 'mm', 'column2': 'mm', 'column3': 'mm'},  # uu1, volatile: u1
        #{'id': 14, 'column1': 'nn', 'column2': 'nn', 'column3': 'nn'}, # uu1, volatile: d
        {'id': 15, 'column1': 'oo', 'column2': 'oo', 'column3': 'oo'},  # ud,  volatile: u1
        #{'id': 16, 'column1': 'pp', 'column2': 'pp', 'column3': 'pp'}, # ud,  volatile: d
        {'id': 17, 'column1': 'q', 'column2': 'q', 'column3': 'q'},     # u-,  volatile: u0
        {'id': 18, 'column1': 'rr', 'column2': 'rr', 'column3': 'rr'},  # u-,  volatile: u1
        #{'id': 19, 'column1': 'ss', 'column2': 'ss', 'column3': 'ss'}, # u-,  volatile: d
        {'id': 20, 'column1': 'tt', 'column2': 'tt', 'column3': 'tt'},  # du,  volatile: i0
        {'id': 21, 'column1': 'uu', 'column2': 'uu', 'column3': 'uu'},  # du,  volatile: i1
        {'id': 22, 'column1': 'vv', 'column2': 'vv', 'column3': 'vv'},  # dd,  volatile: i1
        {'id': 23, 'column1': 'w', 'column2': 'w', 'column3': 'w'},     # d-,  volatile: i0
        {'id': 24, 'column1': 'xx', 'column2': 'xx', 'column3': 'xx'},  # d-,  volatile: i1
        {'id': 25, 'column1': 'yy', 'column2': 'yy', 'column3': 'yy'},  # -u,  volatile: u0
        {'id': 26, 'column1': 'zz', 'column2': 'z', 'column3': 'z'},    # -u,  volatile: u1
        #{'id': 27, 'column1': '0', 'column2': '0', 'column3': '0'},    # -u,  volatile: d
        {'id': 28, 'column1': '11', 'column2': '11', 'column3': '11'},  # -d,  volatile: u1
        #{'id': 29, 'column1': '2', 'column2': '2', 'column3': '2'},    # -d,  volatile: d
        {'id': 30, 'column1': '33', 'column2': '33', 'column3': '33'},  # --,  volatile: u1
        #{'id': 31, 'column1': '4', 'column2': '4', 'column3': '4'},    # --,  volatile: d
    ],
    'record_hashes': [
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '10,', 'record_hash': 'ddcf2d042fb12d69a6aa025091863079'}, # uu0, volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '11,', 'record_hash': '9adfa122c15cd3ea743eb27eab6df352'}, # uu0, volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '12,', 'record_hash': 'f3461235e0adbf30cd2cee1366ed6c82'}, # uu1, volatile: u0
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '13,', 'record_hash': 'a8ff618c7fbe2b038a06f292ff450582'}, # uu1, volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '14,', 'record_hash': 'f3fcc31ed56b1b6acd7923a30b9aea04'}, # uu1, volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '15,', 'record_hash': '69be8901b6ce9f1f11fe7e1da38450d1'}, # ud,  volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '16,', 'record_hash': 'eea5566fa40d87c994f1e25d92db5961'}, # ud,  volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '17,', 'record_hash': '2f3532f5805f395fcd026954212041d7'}, # u-,  volatile: u0
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '18,', 'record_hash': '1154029a4529d3d85dc7efcaddda63d0'}, # u-,  volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '19,', 'record_hash': '1c1fcecd79a5a01daf68f8d3f7cfd945'}, # u-,  volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '20,', 'record_hash': 'b4668e025902f7aa655abed3824eee03'}, # du,  volatile: i0
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '21,', 'record_hash': 'd0ac2408d92044a4d1fd3d55e9beb98e'}, # du,  volatile: i1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '22,', 'record_hash': '3f9cef59dee7f3f5e82d5af2f0614d04'}, # dd,  volatile: i1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '23,', 'record_hash': '100e14214e986ff3c469195cfddbfd80'}, # d-,  volatile: i0
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '24,', 'record_hash': '95ede86563721d7b7ec473e803e93e65'}, # d-,  volatile: i1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '25,', 'record_hash': '493a3bc93b0c031d11099be97a4b5dcd'}, # -u,  volatile: u0
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '26,', 'record_hash': '2c6f8b27720efb588513731308d29bdf'}, # -u,  volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '27,', 'record_hash': '67c51c31e29664a2847164908776158c'}, # -u,  volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '28,', 'record_hash': 'a7b7dfb062dcaf7137918ae95f16b5ae'}, # -d,  volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '29,', 'record_hash': '6815b1e2780e983b736470d3d4a54ca2'}, # -d,  volatile: d
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '30,', 'record_hash': '56988af367780cf608d4fb85ff69f6b1'}, # --,  volatile: u1
        {'sync_name': '__test__', 'section_name': 'records', 'record_id': '31,', 'record_hash': '471bfdf5ab49fd9f67343ba0f5459b16'}, # --,  volatile: d
    ],
}
