/** 供 useMatches() 识别当前是否为 404 视图，避免导航守卫死循环 */
export const NOT_FOUND_HANDLE = { notFound: true as const };
