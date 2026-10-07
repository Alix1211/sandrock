# 샌드락 에셋 이름표 (케인이 GPT에게 준 그림 명령어 순서 그대로, 2026-10-07 대조 완료)
# 키 = source_sheets/sandrock 의 시트 파일 이름, 값 = (출력 폴더, [(파일이름, 한글이름), ...]) 왼쪽→오른쪽, 위→아래 순서

BUILDINGS = [
    ('city_hall', '시청'), ('workshop', '공방'), ('material_shop', '재료상'), ('general_store', '잡화점'),
    ('blacksmith', '대장간'), ('research_center', '연구센터'), ('recycling', '재활용소'), ('carpentry', '목공소'),
    ('clothing', '의류점'), ('pharmacy', '약방'), ('inn', '여관'), ('restaurant', '식당'), ('guild', '길드'),
    ('warehouse', '창고'), ('trading_post', '교역소'), ('post_office', '우체국'), ('mine_office', '광산 관리소'),
    ('ruin_office', '유적 관리소'), ('guard_hq', '경비대'), ('community_hall', '마을회관'), ('residence', '민가'),
    ('mansion', '저택'), ('abandoned', '폐건물'),
]

NPCS = [
    ('general_store', '잡화점'), ('workshop', '공방'), ('carpentry', '목공소'), ('research_center', '연구센터'), ('city_hall', '시청'),
    ('recycling', '재활용소'), ('material_shop', '재료상'), ('blacksmith', '대장간'), ('clothing', '의류점'), ('mine_office', '광산 관리소'),
    ('guild', '길드'), ('post_office', '우체국'), ('inn', '여관'), ('restaurant', '식당'), ('pharmacy', '약방'),
    ('warehouse', '창고'), ('trading_post', '교역소'), ('residence', '민가'), ('ruin_office', '유적 관리소'), ('community_hall', '마을회관'),
    ('mansion', '저택'), ('abandoned', '폐건물'), ('guard_m', '경비대 남'), ('guard_f', '경비대 여'),
]

STATIONS = [
    ('workbench', '작업대'), ('workbench_adv', '고급 작업대'), ('furnace', '용광로'), ('furnace_adv', '고급 용광로'), ('anvil', '모루'), ('cutting_bench', '절단대'),
    ('grinding_bench', '연마대'), ('woodworking_bench', '목공 작업대'), ('assembly_bench', '조립대'), ('machine_bench', '기계 조립대'), ('leather_bench', '가죽 작업대'), ('sewing_bench', '재봉 작업대'),
    ('alchemy_bench', '약제대'), ('dismantle_bench', '분해대'), ('recycle_machine', '재활용 가공대'), ('ore_storage', '광석 보관함'), ('wood_storage', '목재 보관함'), ('parts_storage', '부품 보관함'),
    ('goods_storage', '완성품 보관함'), ('tool_rack', '공구 걸이'), ('shelf', '선반'), ('blueprint_board', '도면 게시판'), ('experiment_table', '실험 테이블'), ('repair_table', '수리 테이블'),
    ('packing_table', '포장 작업대'), ('small_forge', '작은 화로'), ('cooling_tub', '냉각 통'), ('hammer_rack', '망치 거치대'), ('saw_rack', '톱 거치대'), ('tong_rack', '집게 거치대'),
    ('parts_box', '톱니/부품 상자'), ('work_chair', '작업 의자'), ('work_lamp', '작업등'), ('wall_clock', '벽시계'), ('order_board', '주문 게시판'),
]

ICONS = [
    # 시트1
    ('wood', '나무'), ('hardwood', '단단한 나무'), ('oldwood', '고목 조각'), ('sap', '나무 수액'), ('vines', '덩굴'), ('twigs', '나뭇가지'), ('stone', '돌'), ('rough_stone', '거친 석재'),
    ('clay', '점토'), ('sand', '모래'), ('gravel', '자갈'), ('quartz', '석영 조각'), ('copper_ore', '구리 광석'), ('tin_ore', '주석 광석'), ('zinc_ore', '아연 광석'), ('iron_ore', '철광석'),
    ('silver_ore', '은광석'), ('gold_ore', '금광석'), ('coal', '석탄'), ('magnetite', '자철석'), ('crystal_ore', '수정 광석'), ('mana_ore', '마력 광석'), ('plant_fiber', '식물 섬유'), ('herb', '약초'),
    ('red_herb', '붉은 약초'), ('blue_herb', '푸른 약초'), ('mushroom', '버섯'), ('poison_mushroom', '독버섯'), ('wildflower', '야생 꽃'), ('aromatic_herb', '향초'), ('berry', '열매'), ('water_lily', '수련잎'),
    ('swamp_moss', '늪 이끼'), ('scrap_iron', '폐철'), ('broken_glass', '깨진 유리'), ('old_cloth', '헌천 조각'), ('old_rope', '낡은 로프'), ('broken_gear', '고장난 톱니'), ('damaged_sheet', '망가진 판금'), ('ancient_fragment', '고대 파편'),
    # 시트2
    ('ancient_wreck', '고대 기계 잔해'), ('broken_tablet', '부서진 석판'), ('rusty_screw', '녹슨 나사 부품'), ('leather', '가죽'), ('tough_leather', '질긴 가죽'), ('fur_hide', '털가죽'), ('bone', '뼈 조각'), ('fang', '송곳니'),
    ('horn', '뿔 조각'), ('slime', '점액'), ('poison_sac', '독낭'), ('feather', '깃털'), ('spider_thread', '거미줄 실'), ('hive_resin', '벌집 수지'), ('elemental_shard', '정령 파편'), ('ghost_dust', '유령 가루'),
    ('demonstone', '악마석 파편'), ('mana_nucleus', '마력 핵'), ('plank', '판재'), ('hardwood_plank', '단단한 판재'), ('charcoal', '목탄'), ('wooden_handle', '나무 손잡이'), ('timber_beam', '목재 들보'), ('wood_frame', '목재 프레임'),
    ('stone_block', '석재 블록'), ('dressed_stone', '다듬은 석재'), ('slab', '석판'), ('brick', '벽돌'), ('whetstone', '연마석'), ('carved_stone', '조각석'), ('glass', '유리'), ('thick_glass', '두꺼운 유리'),
    ('glass_bottle', '유리병'), ('glass_lens', '유리 렌즈'), ('ceramic_shard', '도자기 조각'), ('ceramic_bowl', '도자기 그릇'), ('copper_ingot', '구리 주괴'), ('tin_ingot', '주석 주괴'), ('brass_ingot', '놋쇠 주괴'), ('iron_ingot', '철 주괴'),
    # 시트3
    ('steel_ingot', '강철 주괴'), ('silver_ingot', '은 주괴'), ('gold_ingot', '금 주괴'), ('mana_metal', '정제 마력 금속'), ('cloth', '천 조각'), ('sturdy_cloth', '튼튼한 천'), ('leather_strap', '가죽끈'), ('leather_plate', '가죽판'),
    ('medicinal_extract', '약용 추출물'), ('concentrated_extract', '농축 약용 추출물'), ('mushroom_powder', '버섯 가루'), ('resin_adhesive', '수지 접착제'), ('poison_extract', '독 추출물'), ('mana_powder', '마력 가루'), ('nails', '못'), ('iron_nails', '철 못'),
    ('metal_plate', '금속 판'), ('steel_plate', '강철 판'), ('metal_rod', '금속 봉'), ('steel_rod', '강철 봉'), ('hinge', '경첩'), ('bracket', '브래킷'), ('chain', '체인'), ('hook', '갈고리'),
    ('small_gear', '작은 톱니'), ('large_gear', '큰 톱니'), ('spring', '스프링'), ('shaft', '회전축'), ('bearing', '베어링'), ('pulley', '도르래'), ('wire', '와이어'), ('pressure_pipe', '압력관'),
    ('valve_part', '밸브 부품'), ('machine_frame', '기계 프레임'), ('rope', '로프'), ('rope_ladder', '밧줄 사다리'), ('handle_part', '손잡이 부품'), ('buckle', '버클'), ('lamp_wick', '램프 심지'), ('lamp_frame', '램프 틀'),
    # 시트4
    ('bottle_cap', '병마개'), ('packing_crate', '포장 상자'), ('reinforced_strap', '보강 가죽 스트랩'), ('tool_pouch', '도구집'), ('mana_core', '마력 코어'), ('spirit_crystal', '정령 결정'), ('rune_plate', '룬 판'), ('rune_lens', '룬 렌즈'),
    ('sealing_ring', '봉인 고리'), ('mana_conductor', '마력 도선'), ('ancient_core', '고대 기계 코어'), ('restored_relic', '복원된 유물 부품'),
]

NODES_HERB = [('herb_bush', '약초 덤불'), ('red_herb_bush', '붉은 약초 덤불'), ('blue_herb_bush', '푸른 약초 덤불'),
              ('fiber_grass', '식물 섬유풀'), ('mushroom_colony', '버섯 군락'), ('poison_mushroom_colony', '독버섯 군락')]
NODES = {
    'node_sheet_ore1.png': [('sap_tree', '수액나무'), ('small_stone_pile', '작은 돌무더기'), ('big_rock', '큰 바위'),
                            ('copper_vein', '구리 광맥'), ('tin_vein', '주석 광맥'), ('zinc_vein', '아연 광맥')],
    'node_sheet_ore2.png': [('iron_vein', '철 광맥'), ('silver_vein', '은 광맥'), ('gold_vein', '금 광맥'),
                            ('crystal_vein', '수정 광맥'), ('mana_vein', '마력 광맥'), ('coal_pile', '석탄 더미')],
    'node_sheet_scrap.png': [('abandoned_box', '버려진 상자'), ('broken_minecart', '고장난 광차'), ('ancient_debris', '고대 잔해더미'),
                             ('glass_shard_pile', '유리 파편 더미'), ('collapsed_stone', '무너진 석재 더미')],
    'node_sheet_flower.png': [('wildflower_patch', '야생 꽃밭'), ('aromatic_patch', '향초 군락'), ('water_lily_node', '수련잎'),
                              ('swamp_moss_node', '늪 이끼'), ('scrap_pile', '폐철 더미'), ('broken_cart', '깨진 수레')],
}

TOOLS = [('axe_stone', '돌 도끼'), ('pick_stone', '돌 곡괭이'), ('axe_copper', '구리 도끼'), ('pick_copper', '구리 곡괭이'),
         ('axe_bronze', '청동 도끼'), ('pick_bronze', '청동 곡괭이'), ('axe_iron', '철 도끼'), ('pick_iron', '철 곡괭이'),
         ('axe_steel', '강철 도끼'), ('pick_steel', '강철 곡괭이'), ('axe_mana', '마력 도끼'), ('pick_mana', '마력 곡괭이'),
         ('axe_mithril', '미스릴 도끼'), ('pick_mithril', '미스릴 곡괭이'), ('axe_magic', '마법 도끼'), ('pick_magic', '마법 곡괭이')]
