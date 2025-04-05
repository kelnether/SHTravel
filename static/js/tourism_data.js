// �9�8 ȷ�� JSON ����ʱʹ�� UTF-8
document.addEventListener("DOMContentLoaded", function () {
    console.log("�9�6 ���δ�����ҳ��������");
    document.documentElement.lang = "zh"; // ȷ�� HTML ������ȷ
});

// �9�8 ������������
async function searchSpot() {
    const poiName = document.getElementById("poiName").value.trim();
    const user_id = "UserA"; // ����ĵ�¼�û�

    if (!poiName) {
        alert("�7�4 �����뾰�����ƣ�");
        return;
    }

    const response = await fetch("/search_api", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=UTF-8" }, // ȷ�� UTF-8 ����
        body: JSON.stringify({ user_id, poiName })
    });

    const data = await response.json();
    updateSearchResult(data.spots);
}

// �9�8 ��Ⱦ�������
function updateSearchResult(spots) {
    const searchDiv = document.getElementById("search-result");
    const outputDiv = document.getElementById("search-output");

    if (spots.length > 0) {
        outputDiv.innerHTML = spots.map(spot => `
            <div class="spot-card">
                <img src="${spot.image}" alt="${spot.name}">
                <div class="spot-info">
                    <div class="spot-name">${spot.name}</div>
                    <div class="spot-category">${spot.category}</div>
                    <div class="spot-score">����: �8�2${spot.score}</div>
                </div>
            </div>
        `).join("");
    } else {
        outputDiv.innerHTML = "<p>�7�4 δ�ҵ���ؾ���</p>";
    }
    searchDiv.style.display = "block";
}

// �9�8 ��ȡ�Ƽ�����
async function fetchRecommendations() {
    const user_id = "UserA"; // ������û� ID

    const response = await fetch("/get_recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=UTF-8" },
        body: JSON.stringify({ user_id })
    });

    const data = await response.json();
    updateRecommendations(data.recommendations);
}

// �9�8 ��Ⱦ�Ƽ�����
function updateRecommendations(recommendations) {
    const recommendationsDiv = document.getElementById("recommendations");
    recommendationsDiv.innerHTML = "<h2>�9�9 ��ĸ��Ի��Ƽ�</h2>";

    recommendations.forEach(spot => {
        recommendationsDiv.innerHTML += `
            <div class="spot-card">
                <img src="${spot.image}" alt="${spot.name}">
                <div class="spot-info">
                    <div class="spot-name">${spot.name}</div>
                    <div class="spot-score">����: �8�2${spot.score}</div>
                </div>
            </div>
        `;
    });
}

// �9�8 ��ҳ�����ʱ�����Ƽ�����
window.onload = fetchRecommendations;
