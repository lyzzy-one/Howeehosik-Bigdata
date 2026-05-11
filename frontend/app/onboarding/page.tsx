'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

const slides = [
  {
    emoji: '🌙',
    title: '혼자 귀가할 때\n불안했던 적 있나요?',
    description: '밤늦게 집에 가는 길, 골목이 무섭고\nCCTV가 있는지 궁금했던 적 있죠?',
  },
  {
    emoji: '📍',
    title: '우리 동네 안전도,\n한눈에 확인해요',
    description: 'CCTV, 가로등, 비상벨, 안심귀갓길까지\nAI가 꼼꼼히 분석해드려요',
  },
  {
    emoji: '🏠',
    title: '이사 전에도,\n자취방 고를 때도',
    description: '여러 동네를 비교해서\n가장 안전한 곳을 찾아보세요',
  },
];

export default function OnboardingPage() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const router = useRouter();

  const handleNext = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1);
    } else {
      // 온보딩 완료 표시
      localStorage.setItem('onboarding_completed', 'true');
      router.push('/');
    }
  };

  const handleSkip = () => {
    localStorage.setItem('onboarding_completed', 'true');
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 to-white flex flex-col">
      {/* 건너뛰기 */}
      <div className="flex justify-end p-4">
        <button
          onClick={handleSkip}
          className="text-gray-500 text-sm hover:text-gray-700"
        >
          건너뛰기
        </button>
      </div>

      {/* 슬라이드 컨텐츠 */}
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <div className="text-8xl mb-8">{slides[currentSlide].emoji}</div>
        <h1 className="text-2xl font-bold text-gray-900 text-center whitespace-pre-line mb-4">
          {slides[currentSlide].title}
        </h1>
        <p className="text-gray-600 text-center whitespace-pre-line">
          {slides[currentSlide].description}
        </p>
      </div>

      {/* 인디케이터 */}
      <div className="flex justify-center gap-2 mb-8">
        {slides.map((_, index) => (
          <div
            key={index}
            className={`w-2 h-2 rounded-full transition-colors ${
              index === currentSlide ? 'bg-indigo-600' : 'bg-gray-300'
            }`}
          />
        ))}
      </div>

      {/* 버튼 */}
      <div className="px-8 pb-12">
        <button
          onClick={handleNext}
          className="w-full py-4 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
        >
          {currentSlide < slides.length - 1 ? '다음' : '시작하기'}
        </button>
      </div>
    </div>
  );
}
