"""Explicit OSM activity labels; no inference of live access or experiential suitability."""
ACTIVITY_TAGS = (
    ('amenity','karaoke_box','KTV'),('amenity','cinema','电影院'),('amenity','theatre','剧院'),
    ('amenity','nightclub','夜总会'),('leisure','amusement_arcade','游戏娱乐场所'),
    ('leisure','bowling_alley','保龄球馆'),('leisure','water_park','水上乐园'),
    ('leisure','sports_centre','体育中心'),('leisure','stadium','体育场'),
    ('leisure','pitch','运动场'),('leisure','fitness_centre','健身场所'),
    ('leisure','swimming_pool','游泳场馆'),('leisure','playground','游乐场'),
    ('shop','mall','购物中心'),('landuse','retail','商业区域'),
    ('highway','pedestrian','步行区域'),('amenity','restaurant','餐饮店'),
    ('amenity','cafe','咖啡饮品店'),('amenity','ice_cream','冰淇淋店'))
SPORTS = {'basketball':'篮球','tennis':'网球','football':'足球','soccer':'足球',
          'badminton':'羽毛球','table_tennis':'乒乓球','swimming':'游泳',
          'skateboard':'滑板','fitness':'健身','archery':'射箭','shooting':'射击'}


def enrich_activity(record):
    """Append only explicit tag values; keep all original raw tags and field evidence."""
    tags = record['source_tags']
    clauses = list(record['description_clauses'])
    for key, title in [('sport','运动项目'),('cuisine','餐饮类型'),('access','使用权限标签'),('indoor','室内标签'),('fee','收费标签')]:
        if tags.get(key):
            value = SPORTS.get(tags[key], tags[key]) if key == 'sport' else tags[key]
            clauses.append({'text': f'{title}：{value}（{key}={tags[key]}）', 'source_fields':[key]})
    record['description_clauses'] = clauses
    record['description'] = record['description_zh'] = 'OSM 来源记载：' + '；'.join(c['text'] for c in clauses) + '。'
    record['public_access_verified'] = False
    return record
