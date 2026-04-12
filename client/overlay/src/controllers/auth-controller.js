/**
 * 인증 컨트롤러 facade.
 * 이벤트 바인딩, 인증 세션 흐름, 렌더링은 auth 하위 모듈로 분리한다.
 */

export { initializeAuthFlow } from "./auth/auth-events-controller.js";
export {
    handleAuthExpired,
    handleLoginSubmit,
    handleLogout,
    refreshAuthState,
} from "./auth/auth-session-controller.js";
