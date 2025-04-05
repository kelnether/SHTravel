async function searchSpot() {
    const user_id = "UserA";  // �����û�ID
    const poiName = document.getElementById("poiName").value.trim();

    if (!poiName) {
        document.getElementById("result").innerText = "�7�4 �����뾰�����ƣ�";
        return;
    }

    const response = await fetch("/search_api", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id, poiName })
    });

    const data = await response.json();

    const resultContainer = document.getElementById("result");
    const spotsContainer = document.getElementById("spots-container");

    if (data.found) {
        // ��ʾ�ɹ���Ϣ
        resultContainer.innerText = data.message;

        // ��վɵ��Ƽ����
        spotsContainer.innerHTML = "";

        // ���������б�
        data.spots.forEach(spot => {
            const spotDiv = document.createElement("div");
            spotDiv.classList.add("spot-item");

            spotDiv.innerHTML = `
                <img src="${spot.image}" alt="${spot.name}" style="width: 100px; height: 100px;">
                <h3>${spot.name}</h3>
                <p>���: ${spot.category}</p>
                <p>����: ${spot.score}</p>
            `;

            spotsContainer.appendChild(spotDiv);
        });

    } else {
        // ����ʧ��
        resultContainer.innerText = data.message;
        spotsContainer.innerHTML = ""; // ���֮ǰ������
    }
}
