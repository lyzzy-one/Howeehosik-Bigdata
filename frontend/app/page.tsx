'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import BottomNav from '@/components/BottomNav';

declare global {
  interface Window {
    kakao: any;
  }
}

const KAKAO_API_KEY = 'ccef25915035bf3d514e9fdfb756fc26';

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const router = useRouter();

  // 온보딩 체크
  useEffect(() => {
    const completed = localStorage.getItem('onboarding_completed');
    if (!completed) {
      router.push('/onboarding');
    }
  }, [router]);

  // 카카오맵 스크립트 로드 및 초기화
  useEffect(() => {
    const initializeMap = () => {
      console.log('initializeMap 호출됨');
      const container = document.getElementById('map');
      if (!container) {
        console.error('map container not found');
        setErrorMsg('지도 컨테이너를 찾을 수 없습니다');
        return;
      }

      try {
        const options = {
          center: new window.kakao.maps.LatLng(37.5665, 126.978),
          level: 5,
        };

        mapRef.current = new window.kakao.maps.Map(container, options);
        console.log('지도 생성 완료');
        setMapLoaded(true);

        // 지도 클릭 이벤트
        window.kakao.maps.event.addListener(mapRef.current, 'click', (mouseEvent: any) => {
          const latlng = mouseEvent.latLng;
          setSelectedCoords({ lat: latlng.getLat(), lng: latlng.getLng() });

          if (markerRef.current) {
            markerRef.current.setPosition(latlng);
          } else {
            markerRef.current = new window.kakao.maps.Marker({
              position: latlng,
              map: mapRef.current,
            });
          }

          const geocoder = new window.kakao.maps.services.Geocoder();
          geocoder.coord2Address(latlng.getLng(), latlng.getLat(), (result: any, status: any) => {
            if (status === window.kakao.maps.services.Status.OK) {
              const address = result[0].address.address_name;
              setSelectedAddress(address);
            }
          });
        });
      } catch (err) {
        console.error('지도 초기화 에러:', err);
        setErrorMsg('지도 초기화 실패: ' + String(err));
      }
    };

    const loadKakaoMap = () => {
      console.log('loadKakaoMap 시작');

      // 이미 로드된 경우
      if (window.kakao && window.kakao.maps) {
        console.log('kakao.maps 이미 존재, load 호출');
        window.kakao.maps.load(() => {
          console.log('kakao.maps.load 콜백 실행');
          initializeMap();
        });
        return;
      }

      console.log('스크립트 동적 로드 시작');
      // 스크립트 동적 로드
      const script = document.createElement('script');
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_API_KEY}&libraries=services&autoload=false`;
      script.async = true;

      script.onload = () => {
        console.log('스크립트 로드 완료, kakao:', !!window.kakao);
        if (window.kakao && window.kakao.maps) {
          window.kakao.maps.load(() => {
            console.log('kakao.maps.load 콜백 실행 (스크립트 로드 후)');
            initializeMap();
          });
        } else {
          console.error('kakao.maps가 없음');
          setErrorMsg('카카오맵 SDK 로드 실패');
        }
      };

      script.onerror = (e) => {
        console.error('스크립트 로드 에러:', e);
        setErrorMsg('카카오맵 스크립트 로드 실패');
      };

      document.head.appendChild(script);
    };

    // 약간의 딜레이 후 실행 (DOM이 준비될 때까지)
    const timer = setTimeout(() => {
      loadKakaoMap();
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // 주소 검색
  const handleSearch = () => {
    if (!searchQuery.trim()) return;

    if (!window.kakao || !window.kakao.maps) {
      alert('지도가 아직 로딩 중입니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    const ps = new window.kakao.maps.services.Places();
    ps.keywordSearch(searchQuery, (data: any, status: any) => {
      if (status === window.kakao.maps.services.Status.OK) {
        setSearchResults(data.slice(0, 5));
      } else {
        setSearchResults([]);
        alert('검색 결과가 없습니다.');
      }
    });
  };

  // 검색 결과 선택
  const handleSelectResult = (place: any) => {
    const coords = new window.kakao.maps.LatLng(place.y, place.x);
    setSelectedAddress(place.address_name || place.road_address_name);
    setSelectedCoords({ lat: parseFloat(place.y), lng: parseFloat(place.x) });
    setSearchResults([]);
    setSearchQuery('');

    mapRef.current.setCenter(coords);
    mapRef.current.setLevel(3);

    if (markerRef.current) {
      markerRef.current.setPosition(coords);
    } else {
      markerRef.current = new window.kakao.maps.Marker({
        position: coords,
        map: mapRef.current,
      });
    }
  };

  // 분석하기
  const handleAnalyze = () => {
    if (!selectedCoords) {
      alert('위치를 선택해주세요.');
      return;
    }

    const params = new URLSearchParams({
      lat: selectedCoords.lat.toString(),
      lng: selectedCoords.lng.toString(),
      address: selectedAddress,
    });
    router.push(`/result?${params.toString()}`);
  };

  return (
    <div className="min-h-screen flex flex-col pb-16">
      <Header />

      {/* 검색창 */}
      <div className="px-4 py-3 bg-white border-b border-gray-200 relative z-20">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="주소 또는 장소를 검색하세요"
            className="w-full pl-10 pr-20 py-3 bg-gray-100 border-0 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:bg-white"
          />
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <button
            onClick={handleSearch}
            className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
          >
            검색
          </button>
        </div>

        {/* 검색 결과 */}
        {searchResults.length > 0 && (
          <div className="absolute left-4 right-4 mt-2 bg-white rounded-xl shadow-lg border border-gray-200 z-50 max-h-60 overflow-y-auto">
            {searchResults.map((place, index) => (
              <button
                key={index}
                onClick={() => handleSelectResult(place)}
                className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0"
              >
                <div className="font-medium text-gray-900">{place.place_name}</div>
                <div className="text-sm text-gray-500">{place.address_name}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 지도 */}
      <div className="flex-1 relative" style={{ minHeight: '500px' }}>
        <div id="map" className="absolute inset-0" />

        {!mapLoaded && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-100 z-10">
            <div className="text-center">
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-gray-500 text-sm">지도 로딩 중...</p>
              {errorMsg && <p className="text-red-500 text-xs mt-2">{errorMsg}</p>}
            </div>
          </div>
        )}

        {/* 선택된 주소 & 분석 버튼 */}
        {selectedAddress && (
          <div className="absolute bottom-4 left-4 right-4 bg-white rounded-xl shadow-lg p-4 z-20">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-indigo-600">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-500">선택한 위치</div>
                <div className="font-medium text-gray-900 truncate">{selectedAddress}</div>
              </div>
            </div>
            <button
              onClick={handleAnalyze}
              className="w-full py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
            >
              안전도 분석하기
            </button>
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
