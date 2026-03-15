let userLat = null;
let userLon = null;

// === 1. PRECISE LOCATION TRACKING ===
function requestLocation() {
    if (navigator.geolocation) {
        // Opțiuni pentru precizie maximă (GPS)
        const options = {
            enableHighAccuracy: true, // Asta forțează folosirea GPS-ului exact
            timeout: 10000,           // Așteaptă până la 10 secunde pentru semnal bun
            maximumAge: 0             // Nu folosi o locație veche din cache
        };

        // watchPosition: Se actualizează automat când te miști
        navigator.geolocation.watchPosition(
            (pos) => { 
                userLat = pos.coords.latitude; 
                userLon = pos.coords.longitude; 
                console.log("📍 Precise GPS Update:", userLat, userLon);
            },
            (err) => { 
                console.log("❌ Location error:", err.message); 
            },
            options
        );
    } else {
        console.log("Geolocation is not supported by this browser.");
    }
}

// Pornim urmărirea locației la încărcarea paginii
window.onload = function() { requestLocation(); };

// === 2. MAIN SEND MESSAGE FUNCTION ===
async function sendMessage(manualText = null) {
  const input = document.getElementById("userInput");
  const text = manualText || input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  if (!manualText) input.value = "";

  const box = document.getElementById("messages");
  const typing = document.createElement("div");
  typing.classList.add("typing-indicator");
  typing.id = "typing-indicator";
  typing.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
  box.appendChild(typing);
  box.scrollTop = box.scrollHeight;

  try {
    // Trimitem locația exactă curentă
    const payload = { message: text, lat: userLat, lon: userLon };
    
    const response = await fetch("http://localhost:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (document.getElementById("typing-indicator")) typing.remove();

    const isSafety = data.mode === "safety";
    if (isSafety) {
      const clearBtn = document.getElementById("clearSafetyBtn");
      if (clearBtn) clearBtn.style.display = "inline-block";
      const msgs = document.querySelectorAll(".msg.user");
      if (msgs.length > 0) msgs[msgs.length - 1].classList.add("safety-message");
    }

    addMessage(data.answer, "ai", isSafety);

    // === ACTION EXECUTION ===
    console.log("Action:", data.action);

    if (data.action === "panic_mode") {
        triggerPanic();
    }
    else if (data.action === "open_email" && data.action_payload) {
        setTimeout(() => { window.location.href = data.action_payload; }, 500);
        addActionButton("📧 OPEN EMAIL APP", data.action_payload, "email-fallback-btn");
    }
    else if (data.action === "open_whatsapp" && data.action_payload) {
        setTimeout(() => { window.open(data.action_payload, '_blank'); }, 500);
        addActionButton("💬 OPEN WHATSAPP", data.action_payload, "whatsapp-btn", true);
    }
    else if (data.action === "download_plan" && data.action_payload) {
        // Nume dinamic sau fallback
        const fileName = data.action_filename || "Shopping_List.txt";
        
        downloadFile(data.action_payload, fileName);
        
        const aiMsgs = document.querySelectorAll(".msg.ai");
        if (aiMsgs.length > 0) {
            const btn = document.createElement("button");
            // Extragem numele rețetei pentru buton (estetic)
            let recipeName = fileName.replace("_Recipe_List.txt", "").replace(/_/g, " ");
            btn.textContent = "📄 DOWNLOAD LIST (" + recipeName + ")";
            btn.className = "download-btn";
            btn.onclick = function() { downloadFile(data.action_payload, fileName); };
            appendButtonToMessage(aiMsgs[aiMsgs.length - 1], btn);
        }
    }

  } catch (error) {
    console.error("Error:", error);
    if (document.getElementById("typing-indicator")) typing.remove();
    addMessage("Connection error.", "ai");
  }
}

// === HELPER FUNCTIONS ===

function addMessage(text, sender, isSafety = false) {
  const box = document.getElementById("messages");
  const msgElem = document.createElement("div");
  msgElem.classList.add("msg", sender);
  if (isSafety) msgElem.classList.add("safety-message");
  msgElem.innerHTML = text;
  box.appendChild(msgElem);
  box.scrollTop = box.scrollHeight;
}

function addActionButton(text, url, className, newTab = false) {
  const aiMessages = document.querySelectorAll(".msg.ai");
  const lastAiMsg = aiMessages[aiMessages.length - 1];
  if (lastAiMsg) {
    const btn = document.createElement("a");
    btn.href = url;
    btn.textContent = text;
    btn.className = className;
    if (newTab) btn.target = "_blank";
    appendButtonToMessage(lastAiMsg, btn);
  }
}

function appendButtonToMessage(msgElement, btnElement) {
  msgElement.appendChild(document.createElement("br"));
  msgElement.appendChild(document.createElement("br"));
  msgElement.appendChild(btnElement);
}

function downloadFile(content, filename) {
  const blob = new Blob([content], { type: "text/plain" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

function triggerPanic() {
  window.location.href = "https://www.google.com/search?q=cupcake+recipes";
}
document.addEventListener("keydown", function(event) {
  if (event.key === "Escape") triggerPanic();
});
function toggleHamburgerMenu() {
  const menu = document.getElementById("hamburgerMenu");
  menu.style.display = menu.style.display === "flex" ? "none" : "flex";
}
document.addEventListener("click", function (e) {
  if (!e.target.classList.contains("hamburger")) {
    const menu = document.getElementById("hamburgerMenu");
    if (menu) menu.style.display = "none";
  }
});
document.getElementById("userInput").addEventListener("keydown", function (event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});
function clearSafetyMessages() {
  const msgs = document.querySelectorAll(".safety-message");
  msgs.forEach(msg => msg.remove());
  document.getElementById("clearSafetyBtn").style.display = "none";
}