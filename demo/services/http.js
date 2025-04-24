
/*
  Make HTTP requests (POST messages to API)
*/

class Http {
  async post(url, post_data) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(post_data)
      });
      const data = await response.json();
      return data;
    } catch (error) {
      throw error;
    }
  }
}

export default Http;
