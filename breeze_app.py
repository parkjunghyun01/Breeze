import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from streamlit_geolocation import streamlit_geolocation
from datetime import datetime
import streamlit.components.v1 as components
import requests
import json
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
from datetime import datetime
KAKAO_JS_KEY = st.secrets["kakao_js_key"]
KAKAO_REST_KEY = st.secrets["kakao_rest_key"]
HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

cookies = EncryptedCookieManager(prefix="breeze_", password="secure-password")
if not cookies.ready():
    st.stop()

if "page" not in st.session_state:
    st.session_state.page = "start"

if "route_data" not in st.session_state:
    st.session_state["route_data"] = None
    st.session_state["origin"] = None
    st.session_state["destination"] = None

# 쿠키 로딩
name_cookie = cookies.get("name") or ""
age_cookie = int(cookies.get("age") or 20)
start_date_str = cookies.get("start_date")
start_date_cookie = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
lat_cookie = cookies.get("latitude")
lon_cookie = cookies.get("longitude")


def info_setting_screen():
    st.title("📅 금연 정보 설정")
    st.markdown("#### 이름, 나이, 금연 시작일을 입력하세요")

    name_input = st.text_input("이름", value=name_cookie)
    age_input = st.number_input("나이", 1, 120, value=age_cookie)
    start_date_input = st.date_input("금연 시작일", value=start_date_cookie or datetime.today())

    if st.button("금연 정보 저장"):
        if name_input and age_input:
            cookies.update({
                "name": name_input,
                "age": str(age_input),
                "start_date": start_date_input.strftime("%Y-%m-%d"),
            })
            cookies.save()
            st.session_state.page = "start"
            st.success("금연 정보가 저장되었습니다.")
        else:
            st.warning("모든 정보를 입력하세요.")

def start_screen():
    name = cookies.get("name")
    age = cookies.get("age")
    start_date_str = cookies.get("start_date")

    st.markdown(f"### 🙋‍♂️ {name}님({age}세), 반갑습니다!")

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        days = (datetime.today().date() - start_date).days
        st.markdown(f"##### 금연일: **D + {days}일**")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📍 메인 지도"):
            st.session_state.page = "map"
        if st.button("📅 금연일수 설정"):
            st.session_state.page = "info"  # ← 변경

    with col2:
        if st.button("🚨 신고 목록"):
            st.session_state.page = "aaa"
        if st.button("✍️ 후기 작성"):
            st.session_state.page = "review"

    if st.button("⬅️ 처음으로"):
        st.session_state.page = "start"

# 지도 및 길찾기 화면

def search_keyword(keyword: str, size: int = 10):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {"query": keyword, "size": size}
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json().get("documents", [])

def build_place_label(place: dict) -> str:
    name = place.get("place_name", "-")
    addr = place.get("road_address_name") or place.get("address_name", "")
    return f"{name} | {addr}"

def request_route(org_lon, org_lat, dest_lon, dest_lat):
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{org_lon},{org_lat}",
        "destination": f"{dest_lon},{dest_lat}",
        "priority": "RECOMMEND",
        "alternatives": "false",
        "summary": "false",
    }
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()

def decode_vertexes(vertexes):
    return [(float(vertexes[i + 1]), float(vertexes[i])) for i in range(0, len(vertexes), 2)]

def map_screen():
    st.title("🗺️ 흡연구역 찾기")
    
    geo = streamlit_geolocation()
    if geo and geo.get("latitude") and geo.get("longitude") and "org_lat" not in st.session_state:
        st.session_state["org_lat"] = geo["latitude"]
        st.session_state["org_lon"] = geo["longitude"]
        cookies["latitude"] = str(geo["latitude"])
        cookies["longitude"] = str(geo["longitude"])
        cookies.save()
        st.rerun()  # 강제 갱신

    # 출발 위치 가져오기
    org_lat = st.session_state.get("org_lat") or float(cookies.get("latitude", 37.324181))
    org_lon = st.session_state.get("org_lon") or float(cookies.get("longitude", 127.124412))

    smoke_spots = [
        {"name": "1. 소프트웨어ICT관 소프트웨어ICT관 앞 광장 주출입구 옆", "lat": 37.32248, "lng": 127.127577},
        {"name": "2. 미디어센터 미디어센터 주차장", "lat": 37.322062, "lng": 127.128007},
        {"name": "3. 법정관 법정관 뒤 정자(우측)", "lat": 37.321474, "lng": 127.126648},
        {"name": "4. 퇴계기념중앙도서관 퇴계기념중앙도서관 뒤 정자(우측)", "lat": 37.320702, "lng": 127.127504},
        {"name": "5. 난파음악관 음악관-콘서트홀 사이", "lat": 37.318917, "lng": 127.129376},
        {"name": "6. 사회과학관 사회과학관 앞 광장", "lat": 37.32134, "lng": 127.125696},
        {"name": "7. 2공학관 1공학관-2공학관 사이 광장", "lat": 37.320858, "lng": 127.126087},
        {"name": "8. 3공학관 2공학관-3공학관 사이 광장", "lat": 37.320491, "lng": 127.12656},
        {"name": "9. 미술관 미술관 주차장", "lat": 37.3199, "lng": 127.130969},
        {"name": "10. 체육관 체육관 주출입구 우측", "lat": 37.31913, "lng": 127.13213},
        {"name": "11. 글로벌산학협력관 글로벌산학협력관 앞", "lat": 37.321929, "lng": 127.123705},
        {"name": "12. 평화의광장 정자(족구장 방면)", "lat": 37.320238, "lng": 127.12901},
        {"name": "13. 상경관 상경관-사범관 사이 광장", "lat": 37.32248, "lng": 127.12879},
        {"name": "14. 인문관 인문관-상경관 사이 광장", "lat": 37.321938, "lng": 127.128747},
        {"name": "15. 법학관/대학원동 테니스장 앞 정자", "lat": 37.320837, "lng": 127.129563},
        {"name": "16. 집현재 집현재 주차장 입구 정자", "lat": 37.316946, "lng": 127.12687},
        {"name": "17. 무용관, 웅비홀 무용관 옆 정자", "lat": 37.315641, "lng": 127.127127},
        {"name": "18. 진리관 진리관 주차장 앞 정자", "lat": 37.315313, "lng": 127.127362},
    ]

    if "spot_reviews" not in st.session_state:
        st.session_state["spot_reviews"] = {s["name"]: [] for s in smoke_spots}

    selected = st.selectbox("📍 목적지 흡연구역 선택", [s["name"] for s in smoke_spots])
    dest = next((s for s in smoke_spots if s["name"] == selected), None)

    dest_lat, dest_lon = float(dest["lat"]), float(dest["lng"])
    path_coords = []

    clicked = st.button("길찾기 🚀")

    if clicked:
        if org_lat and org_lon and dest_lat and dest_lon:
            with st.spinner("경로 탐색 중..."):
                st.session_state["route_data"] = request_route(org_lon, org_lat, dest_lon, dest_lat)
                st.session_state["origin"] = (org_lat, org_lon)
                st.session_state["destination"] = (dest_lat, dest_lon)
        else:
            st.warning("출발지 또는 도착지 좌표가 올바르지 않습니다.")

    route_data = st.session_state.get("route_data")
    if route_data:
        route = route_data["routes"][0]
        summary = route["summary"]
        distance_km = summary["distance"] / 1000
        duration_sec = summary["duration"]
        if duration_sec > 100_000:
            duration_sec = duration_sec / 1000
        hours, minutes = divmod(int(duration_sec // 60), 60)

        st.subheader("📊 경로 요약")
        st.write(f"예상 거리: {distance_km:.1f} km")

        path_coords = [coord for section in route["sections"] for road in section.get("roads", []) for coord in decode_vertexes(road["vertexes"])]

    # 지도 렌더링
    path_js = ",".join([f"new kakao.maps.LatLng({lat},{lon})" for lat, lon in path_coords])
    spot_js = json.dumps(smoke_spots)
    polyline = f"var polyline = new kakao.maps.Polyline({{path: [{path_js}], strokeWeight:5, strokeColor:'#FF0000', strokeOpacity:0.8}}); polyline.setMap(map); map.setBounds(polyline.getBounds());" if path_coords else ""

    map_html = f"""
    <html><head><meta charset='utf-8'><meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
    <script src='https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}&libraries=services'></script></head>
    <body style='margin:0;'>
    <div id='map' style='width:100%;height:500px;'></div>
    <script>
    var map = new kakao.maps.Map(document.getElementById('map'), {{
        center: new kakao.maps.LatLng({org_lat}, {org_lon}),
        level: 7
    }});

    new kakao.maps.Marker({{
        position: new kakao.maps.LatLng({org_lat}, {org_lon}),
        title: '내 위치'
    }}).setMap(map);

    var infowindow = new kakao.maps.InfoWindow();

    var spots = {spot_js};
    spots.forEach(function(s) {{
        var markerImage = new kakao.maps.MarkerImage(
            'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
            new kakao.maps.Size(40, 42),
            {{offset: new kakao.maps.Point(13, 37)}}
        );

        var marker = new kakao.maps.Marker({{
            position: new kakao.maps.LatLng(s.lat, s.lng),
            map: map,
            title: s.name,
            image: markerImage
        }});

        kakao.maps.event.addListener(marker, 'click', function() {{
            var content = '<div style="padding:5px;font-size:14px;">' + s.name + '<br></div>';
            infowindow.setContent(content);
            infowindow.open(map, marker);
        }});
    }});

    {polyline}
    </script></body></html>
    """
    components.html(map_html, height=520)

    # # 리뷰 등록
    # st.markdown("### ✍️ 리뷰 등록")
    # col1, col2 = st.columns([2, 1])

    # with col1:
    #     review_text = st.text_area("리뷰를 입력하세요", key="review_input")
    # with col2:
    #     uploaded_image = st.file_uploader("이미지 첨부", type=["jpg", "jpeg", "png"], key="image_input")

    # if st.button("리뷰 등록"):
    #     if review_text.strip():
    #         review_entry = {"text": review_text.strip()}
    #         if uploaded_image:
    #             review_entry["image"] = uploaded_image.getvalue()
    #         st.session_state["spot_reviews"][selected].append(review_entry)
    #         st.success("리뷰가 등록되었습니다.")
    #     else:
    #         st.warning("빈 리뷰는 등록할 수 없습니다.")
            

    # # 리뷰 출력
    # reviews = st.session_state["spot_reviews"].get(selected, [])
    # if reviews:
    #     st.markdown("### 📋 등록된 리뷰")
    #     for idx, review in enumerate(reviews):
    #         col1, col2 = st.columns([8, 1])
    #         with col1:
    #             st.markdown(f"**{idx + 1}.** {review.get('text', '')}")
    #             if "image" in review:
    #                 st.image(review["image"], use_container_width=True)
    #         with col2:
    #             if st.button("❌", key=f"delete_review_{idx}"):
    #                 st.session_state["spot_reviews"][selected].pop(idx)
    #                 st.session_state["refresh_toggle"] = not st.session_state.get("refresh_toggle", False)
    # else:
    #     st.info("아직 등록된 리뷰가 없습니다.")

    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.page = "start"

def aaa():
    # 초기화
    if "reports" not in st.session_state:
        st.session_state.reports = []

    st.title("📢 신고 게시판")

    # 글 작성 영역
    st.subheader("✍️ 새로운 신고 작성")
    report_title = st.text_input("제목")
    report_content = st.text_area("내용 입력")
    report_author = st.text_input("작성자", value="익명")

    if st.button("🚨 신고 등록"):
        if report_title.strip() and report_content.strip():
            new_report = {
                "title": report_title.strip(),
                "content": report_content.strip(),
                "author": report_author.strip(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.session_state.reports.insert(0, new_report)
            st.success("신고가 등록되었습니다.")
        else:
            st.warning("제목과 내용을 입력해 주세요.")

    # 게시글 목록 표시
    st.subheader("📄 신고 목록")

    if st.session_state.reports:
        for idx, r in enumerate(st.session_state.reports):
            with st.expander(f"{idx+1}. {r['title']} ({r['author']}) - {r['timestamp']}"):
                st.write(r["content"])
    else:
        st.info("아직 등록된 신고가 없습니다.")

    if st.button("⬅️ 처음으로"):
        st.session_state.page = "start"

def review():
    # 흡연 구역 목록 (예시)
    smoking_spots = [
    "1. 소프트웨어ICT관 소프트웨어ICT관 앞 광장 주출입구 옆",
    "2. 미디어센터 미디어센터 주차장",
    "3. 법정관 법정관 뒤 정자(우측)",
    "4. 퇴계기념중앙도서관 퇴계기념중앙도서관 뒤 정자(우측)",
    "5. 난파음악관 음악관-콘서트홀 사이",
    "6. 사회과학관 사회과학관 앞 광장",
    "7. 2공학관 1공학관-2공학관 사이 광장",
    "8. 3공학관 2공학관-3공학관 사이 광장",
    "9. 미술관 미술관 주차장",
    "10. 체육관 체육관 주출입구 우측",
    "11. 글로벌산학협력관 글로벌산학협력관 앞",
    "12. 평화의광장 정자(족구장 방면)",
    "13. 상경관 상경관-사범관 사이 광장",
    "14. 인문관 인문관-상경관 사이 광장",
    "15. 법학관/대학원동 테니스장 앞 정자",
    "16. 집현재 집현재 주차장 입구 정자",
    "17. 무용관, 웅비홀 무용관 옆 정자",
    "18. 진리관 진리관 주차장 앞 정자"
]

    # 세션 상태 초기화
    if "reviews_by_spot" not in st.session_state:
        st.session_state.reviews_by_spot = {spot: [] for spot in smoking_spots}

    st.title("📝 흡연 구역별 후기 작성")

    # 흡연 구역 선택
    selected_spot = st.selectbox("후기를 남길 흡연 구역을 선택하세요", smoking_spots)

    # 후기 작성
    st.subheader(f"✍️ '{selected_spot}' 후기 작성")
    review_text = st.text_area("후기를 입력하세요", key="review_input")
    review_author = st.text_input("작성자", value="익명", key="author_input")
    uploaded_image = st.file_uploader("이미지 첨부", type=["jpg", "jpeg", "png"], key="image_input")

    if st.button("📤 후기 등록"):
        if review_text.strip():
            new_review = {
                "text": review_text.strip(),
                "author": review_author.strip(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            if uploaded_image:
                new_review["image"] = uploaded_image.getvalue()
            st.session_state.reviews_by_spot[selected_spot].insert(0, new_review)
            st.success("후기가 등록되었습니다.")
        else:
            st.warning("후기 내용을 입력해주세요.")

    # 후기 목록 출력
    st.subheader(f"📋 '{selected_spot}'에 대한 후기")
    reviews = st.session_state.reviews_by_spot[selected_spot]
    if reviews:
        for idx, r in enumerate(reviews):
            with st.expander(f"{idx+1}. {r['author']} ({r['timestamp']})"):
                st.write(r["text"])
                if "image" in r:
                    st.image(r["image"], use_container_width=True)
    else:
        st.info("아직 작성된 후기가 없습니다.")
    if st.button("⬅️ 처음으로"):
        st.session_state.page = "start"
# 라우터
page = st.session_state.page
if page == "start":
    start_screen()
elif page == "map":
    map_screen()
elif page == "info":
    info_setting_screen()
elif page == "aaa":
    aaa()
elif page == "review":
    review()
    