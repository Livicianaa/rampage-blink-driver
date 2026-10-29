// RAMPAGE BLINK // CORE CONTROLLER CLIENT
let bridge = null;
let currentLang = localStorage.getItem("blink_lang") || "en";

// Hardware CPI Codes Table
const HW_CPI_TABLE = [
  { code: 0x01, cpi: 200 },  { code: 0x02, cpi: 400 },  { code: 0x03, cpi: 600 },
  { code: 0x04, cpi: 800 },  { code: 0x05, cpi: 1000 }, { code: 0x06, cpi: 1200 },
  { code: 0x07, cpi: 1400 }, { code: 0x08, cpi: 1600 }, { code: 0x09, cpi: 1800 },
  { code: 0x0a, cpi: 2000 }, { code: 0x0c, cpi: 2400 }, { code: 0x0d, cpi: 3200 },
  { code: 0x0e, cpi: 4000 }, { code: 0x0f, cpi: 4800 }, { code: 0x10, cpi: 5600 },
  { code: 0x11, cpi: 6400 }, { code: 0x12, cpi: 7200 }, { code: 0x13, cpi: 8000 },
  { code: 0x14, cpi: 8800 }, { code: 0x15, cpi: 9600 }, { code: 0x16, cpi: 10400 },
  { code: 0x17, cpi: 11200 },{ code: 0x18, cpi: 12800 }
];

const I18N = {
  en: {
    coreTag: "[ CORE SYSTEM // VER 0.3.0 ]",
    subtitle: "WUXI INSTANT A825 NATIVE HARDWARE ARCHITECTURE",
    profileLabel: "PROFILE",
    saveToFlash: "SAVE TO FLASH",
    saveToFlashTitle: "Persist configuration into onboard EEPROM Flash",
    saveSuccess: "Configuration successfully persisted to onboard mouse memory (EEPROM Flash).",
    connected: "CONNECTED: ",
    disconnected: "DISCONNECTED",
    nodeSlot: "[ SLOT %s ]",
    slotTitles: {
      1: "LEFT CLICK",
      2: "MIDDLE CLICK // WHEEL",
      3: "RIGHT CLICK",
      4: "BACKWARD BUTTON",
      5: "FORWARD BUTTON",
      6: "DPI LOOP // FIRE"
    },
    keyFunctions: {
      1: "Left Click",
      2: "Middle Click (Wheel)",
      3: "Right Click",
      4: "Backward Button",
      5: "Forward Button",
      6: "DPI Loop",
      9: "Rapid Fire",
      11: "DPI +",
      12: "DPI -",
      23: "LED On/Off",
      0: "Disabled"
    },
    sensorTag: "[ OPTICAL SENSOR // 12800 MAX CPI ]",
    addStage: "ADD STAGE (MAX 3)",
    removeStage: "Remove Stage",
    stageWheelTooltip: "Stage %d Scroll Wheel LED Color (Click to change)",
    effectMode: "EFFECT MODE",
    speed: "SPEED",
    staticSpeed: "STATIC",
    offSpeed: "OFF",
    brightness: "BRIGHTNESS",
    brightMax: "7 (MAX)",
    brightOff: "0 (OFF)",
    colorConfig: "COLOR CONFIGURATION",
    lightingStatus: "LIGHTING STATUS",
    lightingDisabled: "DISABLED",
    ledOffNotice: "LED circuitry is powered off in hardware. Select an effect mode above to turn on.",
    presets: "PRESETS:",
    fineRgbTuning: "FINE RGB TUNING",
    applyAllSlots: "APPLY SELECTED COLOR TO ALL 7 SLOTS",
    applyAllTooltip: "Turn all cycle slots to this color for single-color flow",
    activeSlot: "ACTIVE: SLOT %d (%s)",
    solidSub: "Synchronizes both mouse body and scroll wheel LED. Select any preset or adjust RGB sliders below.",
    modeTitles: {
      0: "SINGLE COLOR BREATHING ACCENT",
      2: "STATIC SOLID COLOR (BODY & WHEEL)",
      4: "MONO WATER FLOW ACCENT",
      5: "COMET TAIL ACCENT",
      8: "FLASHING BLINK ACCENT",
      12: "KEY REACTIVE ACCENT",
      cycle: "GRADIENT THEMES & CYCLE SLOTS"
    },
    ledModes: [
      [0, "Single Color Breathing"],
      [1, "7-Color Rainbow Cycle"],
      [2, "Static / Constant Light"],
      [3, "Flowing Stream (Water Flow)"],
      [4, "Mono Water Flow"],
      [5, "Comet Tail"],
      [6, "Neon Wave"],
      [7, "Live Stream (Ambilight)"],
      [8, "Flashing Blink"],
      [9, "Star Trail (Starlight)"],
      [10, "Ripple Wave"],
      [11, "Enthusiastic / Dance"],
      [12, "Key Reactive Mode"],
      [13, "LED Disabled (Off)"]
    ],
    usbPollingRate: "USB POLLING RATE",
    fireClickInterval: "FIRE / CLICK INTERVAL",
    dockKeys: "KEYS",
    dockSensor: "SENSOR (DPI)",
    dockLighting: "LIGHTING",
    dockPerformance: "PERFORMANCE"
  },
  tr: {
    coreTag: "[ ÇEKİRDEK SİSTEM // SÜRÜM 0.3.0 ]",
    subtitle: "WUXI INSTANT A825 DOĞAL DONANIM MİMARİSİ",
    profileLabel: "PROFİL",
    saveToFlash: "HAFIZAYA KAYDET",
    saveToFlashTitle: "Yapılandırmayı farenin kalıcı EEPROM flash hafızasına kaydet",
    saveSuccess: "Yapılandırma farenin kalıcı donanım hafızasına (EEPROM Flash) başarıyla kaydedildi.",
    connected: "BAĞLANDI: ",
    disconnected: "BAĞLI DEĞİL",
    nodeSlot: "[ YUVA %s ]",
    slotTitles: {
      1: "SOL TIKLAMA",
      2: "ORTA TIKLAMA // TEKERLEK",
      3: "SAĞ TIKLAMA",
      4: "GERİ TUŞU",
      5: "İLERİ TUŞU",
      6: "DPI DÖNGÜSÜ // ATEŞ"
    },
    keyFunctions: {
      1: "Sol Tık",
      2: "Orta Tık (Tekerlek)",
      3: "Sağ Tık",
      4: "Geri Tuşu",
      5: "İleri Tuşu",
      6: "DPI Döngüsü",
      9: "Seri Ateş",
      11: "DPI +",
      12: "DPI -",
      23: "LED Aç/Kapat",
      0: "Devre Dışı"
    },
    sensorTag: "[ OPTİK SENSÖR // 12800 MAKS CPI ]",
    addStage: "KADEME EKLE (MAKS 3)",
    removeStage: "Kademeyi Kaldır",
    stageWheelTooltip: "Kademe %d Tekerlek LED Rengi (Değiştirmek için tıklayın)",
    effectMode: "EFEKT MODU",
    speed: "HIZ",
    staticSpeed: "SABİT",
    offSpeed: "KAPALI",
    brightness: "PARLAKLIK",
    brightMax: "7 (MAKS)",
    brightOff: "0 (KAPALI)",
    colorConfig: "RENK YAPILANDIRMASI",
    lightingStatus: "AYDINLATMA DURUMU",
    lightingDisabled: "DEVRE DIŞI",
    ledOffNotice: "LED devresi donanımda kapatıldı. Mod listesinden bir efekt seçiniz.",
    presets: "HAZIR RENKLER:",
    fineRgbTuning: "HASSAS RGB AYARI",
    applyAllSlots: "SEÇİLEN RENGİ TÜM 7 YUVAYA UYGULA",
    applyAllTooltip: "Tek renkli akış için tüm döngü yuvalarını bu renge dönüştürür",
    activeSlot: "AKTİF: YUVA %d (%s)",
    solidSub: "Gövde ve tekerlek LED rengini kilitler. Aşağıdaki hazır renk paletinden seçin veya RGB kaydırıcılarıyla ayarlayın.",
    modeTitles: {
      0: "TEK RENK NEFES VURGU RENGİ",
      2: "SABİT IŞIK VURGU RENGİ (GÖVDE & TEKERLEK)",
      4: "TEK RENK SU AKIŞI VURGU RENGİ",
      5: "KUYRUKLU YILDIZ VURGU RENGİ",
      8: "FLAŞÖR VURGU RENGİ",
      12: "TUŞ TEPKİ VURGU RENGİ",
      cycle: "GRADYAN TEMALAR & DÖNGÜ YUVALARI"
    },
    ledModes: [
      [0, "Tek Renk Nefes"],
      [1, "7 Renk Döngülü Nefes"],
      [2, "Sabit Işık"],
      [3, "Su Akışı (Flowing Stream)"],
      [4, "Tek Renk Su Akışı"],
      [5, "Kuyruklu Yıldız (Comet Tail)"],
      [6, "Neon Dalgası"],
      [7, "Canlı Akış (Ambilight)"],
      [8, "Flaşör (Flashing Blink)"],
      [9, "Yıldız İzi (Star Trail)"],
      [10, "Dalgalanma (Ripple Wave)"],
      [11, "Dans / Ritim"],
      [12, "Tuş Tepki Modu"],
      [13, "LED Kapalı"]
    ],
    usbPollingRate: "USB BİLDİRİM HIZI (POLLING)",
    fireClickInterval: "SERİ ATEŞ / TIKLAMA ARALIĞI",
    dockKeys: "TUŞLAR",
    dockSensor: "SENSÖR (DPI)",
    dockLighting: "AYDINLATMA",
    dockPerformance: "PERFORMANS"
  }
};

const SINGLE_COLOR_MODES = [0, 2, 4, 5, 8, 12];

// Hardware DPI indicator preset colors
const DPI_PRESET_COLORS = [
  "#fe0000", "#ff017e", "#7e01ff", "#012aff",
  "#017eff", "#00fff1", "#01ffa9", "#29ff01",
  "#ffe401", "#ff5500"
];

let state = {
  activeProfile: 0,
  dpiStages: [{ level: 0, code: 0x11, cpi: 6400, color: "#012aff" }],
  activeDpiIndex: 0,
  dpiColors: ["#fe0000", "#ff017e", "#7e01ff", "#012aff", "#017eff", "#00fff1"],
  pollingHz: 1000,
  fireTimeMs: 10,
  led: {
    mode: 3,
    speed: 5,
    brightness: 7,
    colors: ["#ff0000", "#ff5500", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#8800ff"]
  }
};

// 1. Language Controller
function setLanguage(lang) {
  if (!I18N[lang]) lang = "en";
  currentLang = lang;
  try {
    localStorage.setItem("blink_lang", lang);
  } catch (e) {}

  document.querySelectorAll(".lang-pill").forEach(p => {
    p.classList.toggle("active", p.getAttribute("data-lang") === lang);
  });

  const t = I18N[lang];

  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.innerText = txt;
  };

  setTxt("headerTag", t.coreTag);
  setTxt("headerSubtitle", t.subtitle);
  setTxt("lblProfile", t.profileLabel);
  setTxt("lblSaveFlash", t.saveToFlash);
  const saveBtn = document.getElementById("saveFlashBtn");
  if (saveBtn) saveBtn.title = t.saveToFlashTitle;

  setTxt("lblSensorTag", t.sensorTag);
  setTxt("lblAddStage", t.addStage);

  setTxt("lblEffectMode", t.effectMode);
  setTxt("lblSpeed", t.speed);
  setTxt("lblBright", t.brightness);
  setTxt("lblPresets", t.presets);
  setTxt("lblFineRgb", t.fineRgbTuning);

  setTxt("lblPolling", t.usbPollingRate);
  setTxt("lblFireTime", t.fireClickInterval);

  setTxt("dockLabelKeys", t.dockKeys);
  setTxt("dockLabelSensor", t.dockSensor);
  setTxt("dockLabelLighting", t.dockLighting);
  setTxt("dockLabelPerf", t.dockPerformance);

  document.querySelectorAll("[data-slot-title]").forEach(el => {
    const slot = el.getAttribute("data-slot-title");
    if (t.slotTitles[slot]) el.innerText = t.slotTitles[slot];
  });
  document.querySelectorAll("[data-slot-meta]").forEach(el => {
    const slot = el.getAttribute("data-slot-meta");
    el.innerText = t.nodeSlot.replace("%s", slot.padStart(2, "0"));
  });

  document.querySelectorAll(".anchor-point[data-slot]").forEach(ap => {
    const slot = ap.getAttribute("data-slot");
    if (t.keyFunctions[slot]) ap.title = t.keyFunctions[slot];
  });

  populateKeyDropdowns();
  setupCustomLedDropdown();
  renderColors();
  renderDpiStages();

  if (bridge && bridge.devicePath) {
    const statusEl = document.getElementById("usbStatus");
    if (statusEl) {
      statusEl.querySelector(".status-text").innerText = t.connected + bridge.devicePath;
    }
  }
}

// 2. Initialization
document.addEventListener("DOMContentLoaded", () => {
  initDockIndicator();
  setLanguage(currentLang);
  setupEventListeners();

  setTimeout(() => {
    updateHudLines();
  }, 1400);

  window.addEventListener("resize", updateHudLines);

  // QWebChannel Bridge Connection
  if (typeof QWebChannel !== "undefined") {
    new QWebChannel(qt.webChannelTransport, (channel) => {
      bridge = channel.objects.bridge;
      document.getElementById("usbStatus").querySelector(".status-text").innerText = (I18N[currentLang].connected) + bridge.devicePath;
      loadHardwareState();
    });
  }
});

// 2. Codemisk Floating Dock Navigation
function initDockIndicator() {
  const dock = document.querySelector(".codemisk-dock");
  const indicator = document.getElementById("dockIndicator");
  const items = document.querySelectorAll(".dock-item");

  function moveIndicator(item) {
    indicator.style.left = item.offsetLeft + "px";
    indicator.style.width = item.offsetWidth + "px";
  }

  items.forEach(item => {
    item.addEventListener("click", () => {
      items.forEach(i => i.classList.remove("active"));
      item.classList.add("active");
      moveIndicator(item);

      const targetTab = item.getAttribute("data-tab");
      document.getElementById("stage").setAttribute("data-active-tab", targetTab);
      document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
      });
      const activeTabEl = document.getElementById(targetTab);
      if (activeTabEl) {
        activeTabEl.classList.add("active");
      }
      setTimeout(updateHudLines, 50);
    });
  });

  const activeFirst = document.querySelector(".dock-item.active");
  if (activeFirst) moveIndicator(activeFirst);
}

// 3. Populate Key Dropdowns
function populateKeyDropdowns() {
  const currentKeyFuncs = I18N[currentLang].keyFunctions;
  document.querySelectorAll(".hud-select[data-slot]").forEach(select => {
    const curVal = select.value;
    select.innerHTML = "";
    for (const [code, name] of Object.entries(currentKeyFuncs)) {
      const opt = document.createElement("option");
      opt.value = code;
      opt.innerText = name;
      select.appendChild(opt);
    }
    const slot = select.getAttribute("data-slot");
    if (curVal) {
      select.value = curVal;
    } else {
      if (slot === "1") select.value = "1";
      if (slot === "2") select.value = "2";
      if (slot === "3") select.value = "3";
      if (slot === "4") select.value = "4";
      if (slot === "5") select.value = "5";
      if (slot === "6") select.value = "6";
    }

    if (!select.dataset.listenerAttached) {
      select.dataset.listenerAttached = "true";
      select.addEventListener("change", () => {
        if (bridge) bridge.set_key(parseInt(slot), parseInt(select.value));
      });
    }
  });
}

// 4. Custom Wayland-Friendly LED Dropdown
function setupCustomLedDropdown() {
  const dropdown = document.getElementById("customModeDropdown");
  const trigger = document.getElementById("dropdownTrigger");
  const menu = document.getElementById("dropdownMenu");
  const selectedText = document.getElementById("selectedModeText");
  const modes = I18N[currentLang].ledModes;

  menu.innerHTML = "";
  modes.forEach(([val, name]) => {
    const item = document.createElement("div");
    item.className = `dropdown-item ${val === state.led.mode ? 'active' : ''}`;
    item.setAttribute("data-mode", val);
    item.innerText = name;

    item.addEventListener("click", (e) => {
      e.stopPropagation();
      state.led.mode = val;
      selectedText.innerText = name;
      document.querySelectorAll(".dropdown-item").forEach(di => di.classList.remove("active"));
      item.classList.add("active");
      dropdown.classList.remove("open");
      renderColors();
      triggerLiveLed();
    });
    menu.appendChild(item);
  });

  const curMode = modes.find(m => m[0] === state.led.mode);
  if (curMode && selectedText) {
    selectedText.innerText = curMode[1];
  }

  if (!trigger.dataset.listenerAttached) {
    trigger.dataset.listenerAttached = "true";
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });

    document.addEventListener("click", () => {
      dropdown.classList.remove("open");
    });
  }
}

let activeDpiPicker = null;

function closeDpiColorPicker() {
  if (activeDpiPicker) {
    activeDpiPicker.remove();
    activeDpiPicker = null;
  }
}

function openDpiColorPicker(idx, anchorEl) {
  closeDpiColorPicker();

  const pop = document.createElement("div");
  pop.className = "dpi-popover";

  DPI_PRESET_COLORS.forEach(col => {
    const sw = document.createElement("div");
    sw.className = "dpi-pop-swatch";
    sw.style.backgroundColor = col;
    sw.title = `Set Stage ${idx + 1} Wheel LED to ${col}`;
    sw.addEventListener("click", (e) => {
      e.stopPropagation();
      state.dpiStages[idx].color = col;
      if (!state.dpiColors) state.dpiColors = [];
      state.dpiColors[idx] = col;
      anchorEl.style.backgroundColor = col;
      if (bridge) {
        bridge.set_stage_color(idx, col);
      }
      closeDpiColorPicker();
    });
    pop.appendChild(sw);
  });

  anchorEl.parentElement.appendChild(pop);
  activeDpiPicker = pop;

  setTimeout(() => {
    const onDocClick = (e) => {
      if (!pop.contains(e.target) && e.target !== anchorEl) {
        closeDpiColorPicker();
        document.removeEventListener("click", onDocClick);
      }
    };
    document.addEventListener("click", onDocClick);
  }, 10);
}

// 5. Simplified 1-3 DPI Stages Manager
function renderDpiStages() {
  const container = document.getElementById("dpiStagesList");
  container.innerHTML = "";

  state.dpiStages.forEach((st, idx) => {
    const row = document.createElement("div");
    row.className = `dpi-stage-row ${idx === state.activeDpiIndex ? 'active' : ''}`;
    row.style.position = "relative";

    const badge = document.createElement("div");
    badge.className = "dpi-badge";
    badge.innerText = `S${idx + 1}`;

    const colorBtn = document.createElement("button");
    colorBtn.className = "dpi-color-btn";
    const stageColor = st.color || (state.dpiColors ? state.dpiColors[idx] : null) || DPI_PRESET_COLORS[idx % DPI_PRESET_COLORS.length];
    colorBtn.style.backgroundColor = stageColor;
    colorBtn.title = I18N[currentLang].stageWheelTooltip.replace("%d", idx + 1);

    colorBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      openDpiColorPicker(idx, colorBtn);
    });

    const sliderWrap = document.createElement("div");
    sliderWrap.className = "dpi-slider-wrap";

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = (HW_CPI_TABLE.length - 1).toString();
    const curIdx = HW_CPI_TABLE.findIndex(item => item.code === st.code);
    slider.value = curIdx >= 0 ? curIdx : 15;
    slider.className = "hud-slider";

    const valLabel = document.createElement("span");
    valLabel.className = "mono-val";
    valLabel.style.marginLeft = "12px";
    valLabel.style.width = "75px";
    valLabel.innerText = `${st.cpi} CPI`;

    slider.addEventListener("input", (e) => {
      const selected = HW_CPI_TABLE[parseInt(e.target.value)];
      st.code = selected.code;
      st.cpi = selected.cpi;
      valLabel.innerText = `${selected.cpi} CPI`;
      if (idx === state.activeDpiIndex) {
        document.getElementById("dpiActiveDisplay").innerText = `${selected.cpi} CPI`;
      }
      sendDpiToHardware();
    });

    row.addEventListener("click", (e) => {
      if (e.target.tagName !== "INPUT" && !e.target.classList.contains("dpi-del-btn") && !e.target.classList.contains("dpi-color-btn") && !e.target.classList.contains("dpi-pop-swatch")) {
        state.activeDpiIndex = idx;
        document.querySelectorAll(".dpi-stage-row").forEach((r, ri) => {
          r.classList.toggle("active", ri === idx);
        });
        document.getElementById("dpiActiveDisplay").innerText = `${st.cpi} CPI`;
        sendDpiToHardware();
        if (bridge) {
          const col = st.color || (state.dpiColors ? state.dpiColors[idx] : null) || DPI_PRESET_COLORS[idx % DPI_PRESET_COLORS.length];
          bridge.set_stage_color(idx, col);
        }
      }
    });

    sliderWrap.appendChild(slider);
    row.appendChild(badge);
    row.appendChild(colorBtn);
    row.appendChild(sliderWrap);
    row.appendChild(valLabel);

    if (state.dpiStages.length > 1) {
      const delBtn = document.createElement("button");
      delBtn.className = "dpi-del-btn";
      delBtn.innerHTML = "×";
      delBtn.title = I18N[currentLang].removeStage;
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        state.dpiStages.splice(idx, 1);
        if (state.activeDpiIndex >= state.dpiStages.length) {
          state.activeDpiIndex = state.dpiStages.length - 1;
        }
        renderDpiStages();
        sendDpiToHardware();
      });
      row.appendChild(delBtn);
    }

    container.appendChild(row);
  });

  const addBtn = document.getElementById("dpiAddBtn");
  addBtn.style.display = state.dpiStages.length < 3 ? "flex" : "none";

  const activeStage = state.dpiStages[state.activeDpiIndex];
  if (activeStage) {
    document.getElementById("dpiActiveDisplay").innerText = `${activeStage.cpi} CPI`;
  }
}

// Preset Palettes for in-app color picker - Safe, pure saturated RGB values for physical LEDs
const PRESET_COLORS = [
  "#ff0000", "#ff5500", "#ffaa00", "#ffff00",
  "#66ff00", "#00ff00", "#00ff88", "#00ffff",
  "#0088ff", "#0000ff", "#8800ff", "#ff00ff",
  "#ff007f", "#ffffff"
];

const PRESET_THEMES = [
  { name: "RAINBOW", colors: ["#ff0000", "#ff5500", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#8800ff"] },
  { name: "CYBERPUNK", colors: ["#ff007f", "#8800ff", "#00ffff", "#ff007f", "#8800ff", "#00ffff", "#ffffff"] },
  { name: "NEON WAVE", colors: ["#00ff00", "#00ffff", "#0088ff", "#8800ff", "#ff007f", "#00ff00", "#00ffff"] },
  { name: "FIRE & EMBER", colors: ["#ff0000", "#ff3300", "#ff7700", "#ffaa00", "#ff3300", "#ff0000", "#ffffff"] },
  { name: "DEEP OCEAN", colors: ["#0000ff", "#0044ff", "#0088ff", "#00ffff", "#0088ff", "#0000ff", "#ffffff"] }
];

let selectedColorIndex = 0;
let ledDebounceTimer = null;

function hexToRgb(hex) {
  hex = hex.replace("#", "");
  if (hex.length === 3) {
    hex = hex.split("").map(c => c + c).join("");
  }
  const num = parseInt(hex, 16);
  return {
    r: (num >> 16) & 255,
    g: (num >> 8) & 255,
    b: num & 255
  };
}

function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map(x => {
    const hex = Math.max(0, Math.min(255, x)).toString(16);
    return hex.length === 1 ? "0" + hex : hex;
  }).join("");
}

// 6. Dynamic Color Modes & Swatches
function renderColors() {
  const speedBox = document.getElementById("speedBox");
  const speedSld = document.getElementById("ledSpeedSlider");
  const speedVal = document.getElementById("ledSpeedVal");
  const swatchesPanel = document.getElementById("swatchesPanel");
  const rgbMixer = document.getElementById("rgbMixer");

  const isSingleColor = SINGLE_COLOR_MODES.includes(state.led.mode);
  const isStatic = (state.led.mode === 2);
  const isOff = (state.led.mode === 13);
  const t = I18N[currentLang];

  // Speed slider durumu: Sabit Isik (Mode 2) donanimda hiza sahip degildir
  if (isStatic) {
    if (speedBox) speedBox.classList.add("disabled-box");
    if (speedSld) speedSld.disabled = true;
    if (speedVal) speedVal.innerText = t.staticSpeed;
  } else if (isOff) {
    if (speedBox) speedBox.classList.add("disabled-box");
    if (speedSld) speedSld.disabled = true;
    if (speedVal) speedVal.innerText = t.offSpeed;
  } else {
    if (speedBox) speedBox.classList.remove("disabled-box");
    if (speedSld) speedSld.disabled = false;
    if (speedVal) speedVal.innerText = `${state.led.speed} / 8`;
  }

  if (isOff) {
    const titleEl = document.getElementById("paletteTitle");
    const infoEl = document.getElementById("selectedColorInfo");
    if (titleEl) titleEl.innerText = t.lightingStatus;
    if (infoEl) infoEl.innerText = t.lightingDisabled;
    if (swatchesPanel) swatchesPanel.style.display = "none";
    if (rgbMixer) rgbMixer.style.display = "none";
    const container = document.getElementById("dynamicColorArea");
    if (container) {
      container.innerHTML = "";
      const offNotice = document.createElement("div");
      offNotice.style.padding = "16px";
      offNotice.style.fontFamily = "'JetBrains Mono', monospace";
      offNotice.style.fontSize = "11px";
      offNotice.style.color = "var(--muted)";
      offNotice.innerText = t.ledOffNotice;
      container.appendChild(offNotice);
    }
    return;
  }

  if (swatchesPanel) swatchesPanel.style.display = "flex";
  if (rgbMixer) rgbMixer.style.display = "flex";

  renderColorBadges();
  renderColorSwatches();

  const curCol = isSingleColor ? (state.led.colors[0] || "#ff0000") : (state.led.colors[selectedColorIndex] || "#ff0000");
  updateMixerUi(curCol);
}

function renderColorBadges() {
  const container = document.getElementById("dynamicColorArea");
  const titleEl = document.getElementById("paletteTitle");
  const infoEl = document.getElementById("selectedColorInfo");
  if (!container) return;
  container.innerHTML = "";

  const isSingleColor = SINGLE_COLOR_MODES.includes(state.led.mode);
  const t = I18N[currentLang];

  if (isSingleColor) {
    const activeCol = state.led.colors[0] || "#ff0000";
    if (titleEl) titleEl.innerText = t.modeTitles[state.led.mode] || t.modeTitles[2];
    if (infoEl) infoEl.innerText = activeCol.toUpperCase();

    const wrap = document.createElement("div");
    wrap.className = "solid-color-wrap";

    const badge = document.createElement("div");
    badge.className = "solid-color-badge";
    badge.style.backgroundColor = activeCol;
    badge.style.color = activeCol;

    const info = document.createElement("div");
    info.className = "solid-color-info";

    const hex = document.createElement("div");
    hex.className = "solid-color-hex";
    hex.innerText = activeCol.toUpperCase();

    const sub = document.createElement("div");
    sub.className = "solid-color-sub";
    sub.innerText = t.solidSub;

    info.appendChild(hex);
    info.appendChild(sub);
    wrap.appendChild(badge);
    wrap.appendChild(info);
    container.appendChild(wrap);
  } else {
    if (titleEl) titleEl.innerText = t.modeTitles.cycle;
    const curSlotCol = state.led.colors[selectedColorIndex] || '#fff';
    if (infoEl) infoEl.innerText = t.activeSlot.replace("%d", selectedColorIndex + 1).replace("%s", curSlotCol);

    // Quick Themes Bar
    const themesRow = document.createElement("div");
    themesRow.className = "theme-presets-row";

    PRESET_THEMES.forEach(th => {
      const pill = document.createElement("button");
      pill.className = "theme-pill";
      pill.innerText = th.name;
      pill.addEventListener("click", () => {
        state.led.colors = [...th.colors];
        renderColors();
        triggerLiveLed();
      });
      themesRow.appendChild(pill);
    });
    container.appendChild(themesRow);

    // 7 Crystals Row
    const crystalsRow = document.createElement("div");
    crystalsRow.className = "crystals-row";

    state.led.colors.forEach((col, idx) => {
      const c = document.createElement("div");
      c.className = `color-crystal ${idx === selectedColorIndex ? 'active' : ''}`;
      c.style.backgroundColor = col;
      c.style.color = col;
      c.title = `Slot ${idx + 1} (${col})`;

      c.addEventListener("click", () => {
        selectedColorIndex = idx;
        document.querySelectorAll(".color-crystal").forEach((el, i) => {
          el.classList.toggle("active", i === idx);
        });
        if (infoEl) infoEl.innerText = t.activeSlot.replace("%d", idx + 1).replace("%s", col);
        updateMixerUi(col);
      });

      crystalsRow.appendChild(c);
    });
    container.appendChild(crystalsRow);

    // Apply to all slots button
    const applyAllRow = document.createElement("div");
    applyAllRow.style.display = "flex";
    applyAllRow.style.justifyContent = "flex-end";
    applyAllRow.style.marginTop = "6px";

    const applyAllBtn = document.createElement("button");
    applyAllBtn.className = "apply-all-btn";
    applyAllBtn.innerText = t.applyAllSlots;
    applyAllBtn.title = t.applyAllTooltip;
    applyAllBtn.addEventListener("click", () => {
      const curCol = state.led.colors[selectedColorIndex];
      for (let i = 0; i < state.led.colors.length; i++) {
        state.led.colors[i] = curCol;
      }
      renderColorBadges();
      triggerLiveLed();
    });
    applyAllRow.appendChild(applyAllBtn);
    container.appendChild(applyAllRow);
  }
}

function updateMixerUi(hex) {
  const rgb = hexToRgb(hex);
  const rSld = document.getElementById("mixR");
  const gSld = document.getElementById("mixG");
  const bSld = document.getElementById("mixB");
  const rVal = document.getElementById("mixRVal");
  const gVal = document.getElementById("mixGVal");
  const bVal = document.getElementById("mixBVal");
  const hexVal = document.getElementById("mixerHexVal");

  if (rSld) rSld.value = rgb.r;
  if (gSld) gSld.value = rgb.g;
  if (bSld) bSld.value = rgb.b;
  if (rVal) rVal.innerText = rgb.r;
  if (gVal) gVal.innerText = rgb.g;
  if (bVal) bVal.innerText = rgb.b;
  if (hexVal) {
    hexVal.innerText = hex.toUpperCase();
    hexVal.style.color = hex;
  }
}

function renderColorSwatches() {
  const grid = document.getElementById("swatchesGrid");
  if (!grid) return;
  grid.innerHTML = "";

  PRESET_COLORS.forEach(color => {
    const btn = document.createElement("button");
    btn.className = "swatch-btn";
    btn.style.backgroundColor = color;
    btn.style.color = color;
    btn.title = `Apply ${color}`;

    btn.addEventListener("click", () => {
      applyColor(color, true);
    });

    grid.appendChild(btn);
  });
}

function applyColor(color, updateMixer = true) {
  if (SINGLE_COLOR_MODES.includes(state.led.mode)) {
    for (let i = 0; i < state.led.colors.length; i++) {
      state.led.colors[i] = color;
    }
  } else {
    state.led.colors[selectedColorIndex] = color;
  }
  if (updateMixer) {
    updateMixerUi(color);
  }
  renderColorBadges();
  clearTimeout(ledDebounceTimer);
  ledDebounceTimer = setTimeout(triggerLiveLed, 120);
}

// 7. Calculate and Draw Sutéra 45-degree HUD Lines
function updateHudLines() {
  const svg = document.getElementById("hudSvg");
  svg.innerHTML = "";

  if (!document.getElementById("tab-keys").classList.contains("active")) {
    return;
  }

  const stageRect = document.getElementById("stage").getBoundingClientRect();

  document.querySelectorAll(".anchor-point").forEach(ap => {
    const slot = ap.getAttribute("data-slot");
    const node = document.querySelector(`.hud-floating-node[data-slot="${slot}"]`);
    if (!node) return;

    const apRect = ap.getBoundingClientRect();
    const nodeRect = node.getBoundingClientRect();

    const x1 = apRect.left + apRect.width / 2 - stageRect.left;
    const y1 = apRect.top + apRect.height / 2 - stageRect.top;

    const isLeft = node.classList.contains("node-left");
    const x2 = (isLeft ? nodeRect.right : nodeRect.left) - stageRect.left;
    const y2 = nodeRect.top + nodeRect.height / 2 - stageRect.top;

    const dir = isLeft ? -1 : 1;
    const stub = 20;
    const p1x = x1 + dir * stub;
    const p1y = y1;

    const deltaY = y2 - y1;
    const diag = Math.min(Math.abs(deltaY), Math.max(10, Math.abs(x2 - p1x) * 0.45));
    const p2x = p1x + dir * diag;
    const p2y = y1 + Math.sign(deltaY) * diag;

    const d = `M ${x1} ${y1} L ${p1x} ${p1y} L ${p2x} ${p2y} L ${x2} ${y2}`;

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    path.setAttribute("class", "hud-line");
    path.setAttribute("id", `line-${slot}`);
    svg.appendChild(path);

    node.onmouseenter = () => {
      path.classList.add("active");
      ap.classList.add("active");
    };
    node.onmouseleave = () => {
      path.classList.remove("active");
      ap.classList.remove("active");
    };
  });
}

// 8. Event Listeners
function setupEventListeners() {
  document.getElementById("dpiAddBtn").addEventListener("click", () => {
    if (state.dpiStages.length < 3) {
      const nextCode = state.dpiStages.length === 1 ? 0x0c : 0x18;
      const cpiItem = HW_CPI_TABLE.find(i => i.code === nextCode);
      state.dpiStages.push({
        level: state.dpiStages.length,
        code: nextCode,
        cpi: cpiItem.cpi
      });
      renderDpiStages();
      sendDpiToHardware();
    }
  });

  document.querySelectorAll(".prof-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".prof-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const pIdx = parseInt(btn.getAttribute("data-prof"));
      state.activeProfile = pIdx;
      if (bridge) bridge.set_profile(pIdx);
    });
  });

  document.querySelectorAll("#pollButtons button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#pollButtons button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const hz = parseInt(btn.getAttribute("data-hz"));
      state.pollingHz = hz;
      if (bridge) bridge.set_polling(hz);
    });
  });

  const fireSld = document.getElementById("fireSlider");
  const fireLbl = document.getElementById("fireTimeVal");
  let fireDebounceTimer = null;
  fireSld.addEventListener("input", (e) => {
    fireLbl.innerText = `${e.target.value} ms`;
    state.fireTimeMs = parseInt(e.target.value);
    clearTimeout(fireDebounceTimer);
    fireDebounceTimer = setTimeout(() => {
      if (bridge) bridge.set_fire_time(state.fireTimeMs);
    }, 120);
  });

  const speedSld = document.getElementById("ledSpeedSlider");
  const speedLbl = document.getElementById("ledSpeedVal");
  speedSld.addEventListener("input", (e) => {
    speedLbl.innerText = `${e.target.value} / 8`;
    state.led.speed = parseInt(e.target.value);
    if (bridge && bridge.set_led_params) {
      bridge.set_led_params(state.led.mode, state.led.speed - 1, state.led.brightness);
    }
  });

  const brightSld = document.getElementById("ledBrightSlider");
  const brightLbl = document.getElementById("ledBrightVal");
  brightSld.addEventListener("input", (e) => {
    const t = I18N[currentLang];
    brightLbl.innerText = e.target.value === "0" ? t.brightOff : (e.target.value === "7" ? t.brightMax : `${e.target.value} / 7`);
    state.led.brightness = parseInt(e.target.value);
    if (bridge && bridge.set_led_params) {
      bridge.set_led_params(state.led.mode, state.led.speed - 1, state.led.brightness);
    }
  });

  const rSld = document.getElementById("mixR");
  const gSld = document.getElementById("mixG");
  const bSld = document.getElementById("mixB");
  const rVal = document.getElementById("mixRVal");
  const gVal = document.getElementById("mixGVal");
  const bVal = document.getElementById("mixBVal");
  const hexVal = document.getElementById("mixerHexVal");

  function onMixerInput() {
    const r = parseInt(rSld.value);
    const g = parseInt(gSld.value);
    const b = parseInt(bSld.value);
    if (rVal) rVal.innerText = r;
    if (gVal) gVal.innerText = g;
    if (bVal) bVal.innerText = b;
    const hex = rgbToHex(r, g, b);
    if (hexVal) {
      hexVal.innerText = hex.toUpperCase();
      hexVal.style.color = hex;
    }
    applyColor(hex, false);
  }

  if (rSld && gSld && bSld) {
    rSld.addEventListener("input", onMixerInput);
    gSld.addEventListener("input", onMixerInput);
    bSld.addEventListener("input", onMixerInput);
  }

  document.querySelectorAll(".lang-pill").forEach(btn => {
    btn.addEventListener("click", () => {
      const lang = btn.getAttribute("data-lang");
      setLanguage(lang);
    });
  });

  document.getElementById("saveFlashBtn").addEventListener("click", () => {
    if (bridge) {
      bridge.save_flash();
      alert(I18N[currentLang].saveSuccess);
    }
  });
}

let dpiDebounceTimer = null;

function sendDpiToHardware() {
  if (!bridge) return;
  clearTimeout(dpiDebounceTimer);
  dpiDebounceTimer = setTimeout(() => {
    const codes = [HW_CPI_TABLE[0].code, HW_CPI_TABLE[1].code, HW_CPI_TABLE[2].code, HW_CPI_TABLE[3].code, HW_CPI_TABLE[4].code, HW_CPI_TABLE[5].code];
    let mask = 0;
    state.dpiStages.forEach((st, i) => {
      codes[i] = st.code;
      mask |= (1 << i);
    });
    bridge.set_dpi_state(JSON.stringify({
      codes: codes,
      mask: mask,
      level: state.activeDpiIndex
    }));
  }, 100);
}

function triggerLiveLed() {
  if (!bridge) return;
  bridge.set_led(
    state.led.mode,
    state.led.speed - 1,
    state.led.brightness,
    JSON.stringify(state.led.colors)
  );
}

// 9. Load Hardware State
function loadHardwareState() {
  if (!bridge) return;
  bridge.get_state(function(res) {
    let hw;
    try {
      hw = JSON.parse(res);
    } catch (e) {
      console.error("JSON parse error:", e, res);
      return;
    }

    state.activeProfile = hw.profile;
    document.querySelectorAll(".prof-btn").forEach((b, i) => {
      b.classList.toggle("active", i === hw.profile);
    });

    if (hw.keys) {
      hw.keys.forEach(([slot, code]) => {
        const sel = document.querySelector(`.hud-select[data-slot="${slot}"]`);
        if (sel) sel.value = code.toString();
      });
    }

    if (hw.polling) {
      state.pollingHz = hw.polling;
      document.querySelectorAll("#pollButtons button").forEach(b => {
        b.classList.toggle("active", parseInt(b.getAttribute("data-hz")) === hw.polling);
      });
    }

    if (hw.fireTime !== undefined) {
      state.fireTimeMs = hw.fireTime;
      const fSld = document.getElementById("fireSlider");
      if (fSld) fSld.value = hw.fireTime;
      const fVal = document.getElementById("fireTimeVal");
      if (fVal) fVal.innerText = `${hw.fireTime} ms`;
    }

    if (hw.dpiColors && hw.dpiColors.length > 0) {
      state.dpiColors = hw.dpiColors;
    }

    if (hw.dpiCodes && hw.dpiCodes.length > 0) {
      state.activeDpiIndex = Math.min(hw.dpiLevel !== undefined ? hw.dpiLevel : 0, 2);
      state.dpiStages = [];
      const numStages = Math.min(3, Math.max(1, (hw.dpiMask ? [0, 1, 2].filter(i => (hw.dpiMask >> i) & 1).length : 1)));
      for (let i = 0; i < numStages; i++) {
        const cCode = hw.dpiCodes[i] || 0x11;
        const cpiItem = HW_CPI_TABLE.find(x => x.code === cCode) || { cpi: 6400 };
        const stageCol = (state.dpiColors && state.dpiColors[i]) ? state.dpiColors[i] : DPI_PRESET_COLORS[i % DPI_PRESET_COLORS.length];
        state.dpiStages.push({
          level: i,
          code: cCode,
          cpi: cpiItem.cpi,
          color: stageCol
        });
      }
      if (state.activeDpiIndex >= state.dpiStages.length) {
        state.activeDpiIndex = 0;
      }
      renderDpiStages();
    }

    if (hw.led) {
      // Eğer mod 13 (kapalı) ise varsayılan olarak su akışı (3) aktif et ki ışıklar yansın
      const effectiveMode = (hw.led.mode === 13) ? 3 : hw.led.mode;
      state.led.mode = effectiveMode;
      state.led.speed = hw.led.speed + 1;
      state.led.brightness = hw.led.brightness !== undefined ? hw.led.brightness : 7;
      if (hw.led.colors && hw.led.colors.length > 0) {
        state.led.colors = hw.led.colors;
      }

      const modeTuple = I18N[currentLang].ledModes.find(m => m[0] === state.led.mode);
      const modeName = modeTuple ? modeTuple[1] : "Flowing Stream";
      const selText = document.getElementById("selectedModeText");
      if (selText) selText.innerText = modeName;

      document.querySelectorAll(".dropdown-item").forEach(di => {
        di.classList.toggle("active", parseInt(di.getAttribute("data-mode")) === state.led.mode);
      });

      const sSld = document.getElementById("ledSpeedSlider");
      if (sSld) sSld.value = state.led.speed.toString();
      const sVal = document.getElementById("ledSpeedVal");
      if (sVal) sVal.innerText = `${state.led.speed} / 8`;

      const bSld = document.getElementById("ledBrightSlider");
      if (bSld) bSld.value = state.led.brightness.toString();
      const bVal = document.getElementById("ledBrightVal");
      if (bVal) bVal.innerText = state.led.brightness === 0 ? "0 (OFF)" : (state.led.brightness === 7 ? "7 (MAX)" : `${state.led.brightness} / 7`);

      renderColors();
    }
  });
}
