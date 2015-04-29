{
    'records': [
        {'id': 1, 'column1': 'aa', 'column2': 'aa', 'column3': 'aa'},  # ii0, volatile: u1
        {'id': 2, 'column1': 'bb', 'column2': 'bb', 'column3': 'bb'},  # ii0, volatile: d
        {'id': 3, 'column1': 'cc', 'column2': 'cc', 'column3': 'cc'},  # ii1, volatile: u0
        {'id': 4, 'column1': 'dd', 'column2': 'd', 'column3': 'd'},    # ii1, volatile: u1
        {'id': 5, 'column1': 'ee', 'column2': 'e', 'column3': 'e'},    # ii1, volatile: d
        #                                                              # i-,  volatile: u1
        #                                                              # i-,  volatile: d
        {'id': 8, 'column1': 'hh', 'column2': 'hh', 'column3': 'hh'},  # -i,  volatile: i0
        {'id': 9, 'column1': 'ii', 'column2': 'i', 'column3': 'i'},    # -i,  volatile: i1
        {'id': 10, 'column1': 'jj', 'column2': 'jj', 'column3': 'jj'}, # uu0, volatile: u1
        {'id': 11, 'column1': 'kk', 'column2': 'kk', 'column3': 'kk'}, # uu0, volatile: d
        {'id': 12, 'column1': 'll', 'column2': 'll', 'column3': 'll'}, # uu1, volatile: u0
        {'id': 13, 'column1': 'mm', 'column2': 'mm', 'column3': 'm'},  # uu1, volatile: u1
        {'id': 14, 'column1': 'nn', 'column2': 'n', 'column3': 'n'},   # uu1, volatile: d
        #{'id': 15, 'column1': 'o', 'column2': 'o', 'column3': 'o'},   # ud,  volatile: u1
        #{'id': 16, 'column1': 'p', 'column2': 'p', 'column3': 'p'},   # ud,  volatile: d
        {'id': 17, 'column1': 'q', 'column2': 'q', 'column3': 'q'},    # u-,  volatile: u0
        {'id': 18, 'column1': 'r', 'column2': 'r', 'column3': 'r'},    # u-,  volatile: u1
        {'id': 19, 'column1': 's', 'column2': 's', 'column3': 's'},    # u-,  volatile: d
        {'id': 20, 'column1': 'tt', 'column2': 'tt', 'column3': 'tt'}, # du,  volatile: i0
        {'id': 21, 'column1': 'uu', 'column2': 'u', 'column3': 'u'},   # du,  volatile: i1
        #{'id': 22, 'column1': 'v', 'column2': 'v', 'column3': 'v'},   # dd,  volatile: i1
        {'id': 23, 'column1': 'w', 'column2': 'w', 'column3': 'w'},    # d-,  volatile: i0
        {'id': 24, 'column1': 'x', 'column2': 'x', 'column3': 'x'},    # d-,  volatile: i1
        {'id': 25, 'column1': 'yy', 'column2': 'yy', 'column3': 'yy'}, # -u,  volatile: u0
        {'id': 26, 'column1': 'zz', 'column2': 'z', 'column3': 'z'},   # -u,  volatile: u1
        {'id': 27, 'column1': '00', 'column2': '00', 'column3': '00'}, # -u,  volatile: d
        #{'id': 28, 'column1': '1', 'column2': '1', 'column3': '1'},   # -d,  volatile: u1
        #{'id': 29, 'column1': '2', 'column2': '2', 'column3': '2'},   # -d,  volatile: d
        {'id': 30, 'column1': '3', 'column2': '3', 'column3': '3'},    # --,  volatile: u1
        {'id': 31, 'column1': '4', 'column2': '4', 'column3': '4'},    # --,  volatile: d
    ],
    'record_hashes': [
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '1,', 'record_hash': 'f05c4e469d21aac365fecd512f7a7dde'}, # ii0, volatile: u1
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '2,', 'record_hash': '5723533d6287c82d5aea7a905f424a2b'}, # ii0, volatile: d
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '3,', 'record_hash': '2fec5278c6a8cc542e2810fb9b1cc55c'}, # ii1, volatile: u0
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '4,', 'record_hash': 'd449f95710bef4fa7044f758f0b7b010'}, # ii1, volatile: u1
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '5,', 'record_hash': 'ecf6bf0f43e7c06d6ed38384f0f17b5d'}, # ii1, volatile: d
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '6,', 'record_hash': 'f3cb440b2fae1ac3a0c56e7aa4a06bc4'}, # i-,  volatile: u1
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '7,', 'record_hash': '711d14ace2ff5c6f8d67be57ff0f375c'}, # i-,  volatile: d
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '8,', 'record_hash': '7d9c5a64f319665e502c25e346b3c4a2'}, # -i,  volatile: i0
        #{'sync_name': '__test__', 'section_name': 'records', 'record_id': '9,', 'record_hash': 'e02583bb79314a71876fd642a4c582f1'}, # -i,  volatile: i1
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