
export const fetchWithBoardId = async (url: string, options?: RequestInit): Promise<Response> => {
  const boardId = localStorage.getItem('boardId');
  let newUrl = url;

  if (boardId && newUrl.includes(':8200/')) {
    try {
      const urlObject = new URL(newUrl);
      urlObject.searchParams.append('board_id', boardId);
      newUrl = urlObject.toString();
    } catch (error) {
      console.error('Failed to construct URL:', error);
      // Fallback to original URL if construction fails
    }
  }

  return fetch(newUrl, options);
};
