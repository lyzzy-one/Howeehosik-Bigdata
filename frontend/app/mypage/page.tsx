'use client';

import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import BottomNav from '@/components/BottomNav';

export default function MyPage() {
  const router = useRouter();

  const menuItems = [
    { icon: '📋', label: '검색 기록', href: '/history' },
    { icon: '📊', label: '저장된 비교', href: '/compare' },
    { icon: '🔔', label: '알림 설정', href: '#', disabled: true },
    { icon: '❓', label: '자주 묻는 질문', href: '#', disabled: true },
    { icon: '📝', label: '의견 보내기', href: '#', disabled: true },
    { icon: '📄', label: '이용약관', href: '#', disabled: true },
    { icon: '🔒', label: '개인정보처리방침', href: '#', disabled: true },
  ];

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header title="마이페이지" />

      <div className="max-w-lg mx-auto">
        {/* 프로필 영역 */}
        <div className="bg-white p-6 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-indigo-600">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="font-semibold text-gray-900">게스트</div>
              <div className="text-sm text-gray-500">로그인하고 더 많은 기능을 이용하세요</div>
            </div>
          </div>
          <button
            onClick={() => router.push('/login')}
            className="w-full mt-4 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
          >
            로그인 / 회원가입
          </button>
        </div>

        {/* 통계 */}
        <div className="bg-white p-4 border-b border-gray-200">
          <div className="flex justify-around text-center">
            <div>
              <div className="text-2xl font-bold text-indigo-600">
                {typeof window !== 'undefined'
                  ? JSON.parse(localStorage.getItem('search_history') || '[]').length
                  : 0}
              </div>
              <div className="text-sm text-gray-500">검색 기록</div>
            </div>
            <div className="w-px bg-gray-200" />
            <div>
              <div className="text-2xl font-bold text-indigo-600">
                {typeof window !== 'undefined'
                  ? JSON.parse(localStorage.getItem('saved_comparisons') || '[]').length
                  : 0}
              </div>
              <div className="text-sm text-gray-500">저장된 비교</div>
            </div>
          </div>
        </div>

        {/* 메뉴 */}
        <div className="bg-white">
          {menuItems.map((item, index) => (
            <button
              key={index}
              onClick={() => !item.disabled && router.push(item.href)}
              disabled={item.disabled}
              className={`w-full px-6 py-4 flex items-center justify-between border-b border-gray-100 last:border-0 ${
                item.disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{item.icon}</span>
                <span className="text-gray-700">{item.label}</span>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          ))}
        </div>

        {/* 버전 정보 */}
        <div className="p-6 text-center text-sm text-gray-400">
          안심귀가 v1.0.0
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
