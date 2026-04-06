(self.webpackChunk_N_E = self.webpackChunk_N_E || []).push([
  [4988],
  {
    34496: function (e, t, n) {
      Promise.resolve().then(n.bind(n, 46469));
    },
    49211: function (e, t, n) {
      "use strict";
      var a = n(99623),
        i = { "text/plain": "Text", "text/html": "Url", default: "Text" };
      e.exports = function (e, t) {
        var n,
          r,
          l,
          o,
          c,
          s,
          u,
          p,
          d = !1;
        (t || (t = {}), (l = t.debug || !1));
        try {
          if (
            ((c = a()),
            (s = document.createRange()),
            (u = document.getSelection()),
            ((p = document.createElement("span")).textContent = e),
            (p.ariaHidden = "true"),
            (p.style.all = "unset"),
            (p.style.position = "fixed"),
            (p.style.top = 0),
            (p.style.clip = "rect(0, 0, 0, 0)"),
            (p.style.whiteSpace = "pre"),
            (p.style.webkitUserSelect = "text"),
            (p.style.MozUserSelect = "text"),
            (p.style.msUserSelect = "text"),
            (p.style.userSelect = "text"),
            p.addEventListener("copy", function (n) {
              if ((n.stopPropagation(), t.format)) {
                if ((n.preventDefault(), void 0 === n.clipboardData)) {
                  (l && console.warn("unable to use e.clipboardData"),
                    l && console.warn("trying IE specific stuff"),
                    window.clipboardData.clearData());
                  var a = i[t.format] || i.default;
                  window.clipboardData.setData(a, e);
                } else
                  (n.clipboardData.clearData(),
                    n.clipboardData.setData(t.format, e));
              }
              t.onCopy && (n.preventDefault(), t.onCopy(n.clipboardData));
            }),
            document.body.appendChild(p),
            s.selectNodeContents(p),
            u.addRange(s),
            !document.execCommand("copy"))
          )
            throw Error("copy command was unsuccessful");
          d = !0;
        } catch (a) {
          (l && console.error("unable to copy using execCommand: ", a),
            l && console.warn("trying IE specific stuff"));
          try {
            (window.clipboardData.setData(t.format || "text", e),
              t.onCopy && t.onCopy(window.clipboardData),
              (d = !0));
          } catch (a) {
            (l && console.error("unable to copy using clipboardData: ", a),
              l && console.error("falling back to prompt"),
              (n =
                "message" in t
                  ? t.message
                  : "Copy to clipboard: #{key}, Enter"),
              (r =
                (/mac os x/i.test(navigator.userAgent) ? "⌘" : "Ctrl") + "+C"),
              (o = n.replace(/#{\s*key\s*}/g, r)),
              window.prompt(o, e));
          }
        } finally {
          (u &&
            ("function" == typeof u.removeRange
              ? u.removeRange(s)
              : u.removeAllRanges()),
            p && document.body.removeChild(p),
            c());
        }
        return d;
      };
    },
    99623: function (e) {
      e.exports = function () {
        var e = document.getSelection();
        if (!e.rangeCount) return function () {};
        for (
          var t = document.activeElement, n = [], a = 0;
          a < e.rangeCount;
          a++
        )
          n.push(e.getRangeAt(a));
        switch (t.tagName.toUpperCase()) {
          case "INPUT":
          case "TEXTAREA":
            t.blur();
            break;
          default:
            t = null;
        }
        return (
          e.removeAllRanges(),
          function () {
            ("Caret" === e.type && e.removeAllRanges(),
              e.rangeCount ||
                n.forEach(function (t) {
                  e.addRange(t);
                }),
              t && t.focus());
          }
        );
      };
    },
    35571: function (e, t, n) {
      "use strict";
      n.d(t, {
        i: function () {
          return c;
        },
        Z: function () {
          return u;
        },
      });
      var a = n(34912),
        i = n(81196);
      let r = (e) => {
        if (!e) return !1;
        let t = Number(e);
        return !isNaN(t) && t >= 1e6;
      };
      var l = n(96386);
      let o = "/dynamicpricing",
        c = {
          enhancePriceHistoryPath: "".concat(o, "/enhance-price/history"),
          getItemGroupsByItemIds: "".concat(o, "/items"),
          getItemGroupsByItemId: "".concat(o, "/items/group/{itemId}"),
          requestEnhanceGroupItems: "".concat(o, "/stats/enhance-group"),
          getEnhanceGroupItems: "".concat(o, "/stats/enhance-group/items"),
          getLatestEnhancePrices: "".concat(o, "/enhance-price/latest"),
          getEnhanceCostHistory: "".concat(o, "/stats/enhance-cost/history"),
          getEnhanceCountHistory: "".concat(o, "/stats/enhance-count/history"),
          getEnhanceCount: "".concat(o, "/stats/enhance-count"),
          getEnhanceCost: "".concat(o, "/stats/enhance-cost"),
          getEnhanceType: "".concat(o, "/enhance-type/{itemId}"),
          getEnhanceLimit: "".concat(o, "/enhance-limit"),
          getEnhanceItemTopCount: "".concat(o, "/items/top-count"),
          getSearchItemKeyword: (e) =>
            "".concat(o, "/items/search/").concat(encodeURIComponent(e)),
        };
      class s extends l.Z {
        async getEnhanceTopCount() {
          return this.fetch(c.getEnhanceItemTopCount, { method: "GET" });
        }
        async getEnhanceLimit(e) {
          let { item_id: t } = e;
          return this.fetch(c.getEnhanceLimit, {
            method: "GET",
            params: { item_id: t },
          });
        }
        async getEnhanceType(e) {
          if (!r(e)) throw Error("Invalid Item ID");
          return this.fetch(
            this.replacePathParams(c.getEnhanceType, { itemId: e }),
            { method: "GET" },
          );
        }
        async getSearchItem(e) {
          let { itemName: t } = e,
            n = c.getSearchItemKeyword(t);
          return this.fetch(n, { method: "GET" });
        }
        async getEnhanceGroupItems(e) {
          return this.fetch(c.getEnhanceGroupItems, {
            method: "GET",
            params: e,
          });
        }
        async getEnhanceCostHistory(e) {
          let t = "".concat(c.getEnhanceCostHistory, "?dayType=").concat(e);
          return this.fetch(t, { method: "GET" });
        }
        async getEnhanceCountHistory(e) {
          let t = "".concat(c.getEnhanceCountHistory, "?dayType=").concat(e);
          return this.fetch(t, { method: "GET" });
        }
        async requestEnhanceGroupItems(e) {
          return this.fetch(c.requestEnhanceGroupItems, {
            method: "POST",
            body: JSON.stringify(e),
          });
        }
        async getItemGroupByItemId(e) {
          return this.fetch(
            this.replacePathParams(c.getItemGroupsByItemId, {
              itemId: "".concat(e),
            }),
            { method: "GET" },
          );
        }
        async getItemGroupsByItemIds(e) {
          return this.fetch(c.getItemGroupsByItemIds, {
            method: "POST",
            body: JSON.stringify({ itemId: e }),
          });
        }
        async getLatestEnhancePrices(e, t) {
          return this.fetch(c.getLatestEnhancePrices, {
            method: "GET",
            params: { itemId: e, period: t },
          });
        }
        async getEnhanceCount() {
          return this.fetch(c.getEnhanceCount, { method: "GET" });
        }
        async getEnhanceCost() {
          return this.fetch(c.getEnhanceCost, { method: "GET" });
        }
        async getHistory(e) {
          let {
            itemId: t,
            itemUpgrade: n,
            itemUpgradeType: a,
            itemUpgradeSubType: i,
            timePeriodType: r,
            maxTimestamp: l,
            minTimestamp: o,
          } = e;
          return this.fetch(c.enhancePriceHistoryPath, {
            method: "GET",
            params: {
              ...(t && { itemId: t }),
              ...(n && { itemUpgrade: n }),
              ...(a && { itemUpgradeType: a }),
              ...(i && { itemUpgradeSubType: i }),
              ...(r && { period: r }),
              ...(o && { minTimestamp: o }),
              ...(l && { maxTimestamp: l }),
            },
          });
        }
        constructor(e) {
          var t;
          (super(e),
            (this.ssrBaseUrl =
              null !== (t = null == e ? void 0 : e.ssrBaseUrl) && void 0 !== t
                ? t
                : a.nN.rewriteTarget),
            (this.apiPath = (null == e ? void 0 : e.apiPath)
              ? (0, i.b)(this.baseURL, e.apiPath)
              : (0, i.b)(this.baseURL, a.nN.rewriteSource)));
        }
      }
      var u = s;
    },
    49171: function (e, t, n) {
      "use strict";
      var a = n(63861),
        i = n(35571);
      let r = async (e) => {
        let t = new i.Z();
        try {
          return { data: (await t.getSearchItem({ itemName: e })).items };
        } catch (e) {
          throw (console.error("Error fetching data:::::", e), e);
        }
      };
      t.Z = function (e) {
        let t = e && e.trim().length > 0;
        return (0, a.ZP)(t ? e : null, () => r(e), {
          revalidateOnFocus: !1,
          revalidateOnReconnect: !1,
          shouldRetryOnError: !0,
          dedupingInterval: 6e4,
          onErrorRetry: (e, t, n, a, i) => {
            let { retryCount: r } = i;
            404 !== e.status &&
              (r >= 3 || setTimeout(() => a({ retryCount: r }), 5e3));
          },
        });
      };
    },
    46469: function (e, t, n) {
      "use strict";
      (n.r(t),
        n.d(t, {
          default: function () {
            return tV;
          },
        }));
      var a,
        i = n(57437),
        r = n(71620),
        l = n.n(r),
        o = n(81062),
        c = n(3093),
        s = n.n(c),
        u = n(36760),
        p = n.n(u);
      function d(e) {
        let { className: t, title: n, children: a } = e;
        return (0, i.jsxs)("section", {
          className: p()(t, s().informationSection),
          children: [
            (0, i.jsx)(o.Z, {
              as: "h3",
              type: "heading-xxl-bold",
              colorToken: { color: "text-icon-primary" },
              children: n,
            }),
            (0, i.jsx)("div", {
              className: s().informationSectionContents,
              children: a,
            }),
          ],
        });
      }
      var m = n(66718),
        h = n(99451),
        f = n.n(h),
        g = function (e) {
          let { className: t, children: n } = e;
          return (0, i.jsx)("div", {
            className: p()(t, f().guideText),
            children: (0, i.jsx)("div", {
              className: f().guideDesc,
              children: (0, i.jsxs)(o.Z, {
                type: "body-s-regular-wide",
                colorToken: { color: "text-icon-secondary" },
                style: { display: "flex", gap: "4px" },
                children: [
                  (0, i.jsx)(m.Z, {
                    size: "medium",
                    color: "gray-400",
                    type: "InfoFilled",
                  }),
                  n,
                ],
              }),
            }),
          });
        },
        y = n(53415),
        x = n.n(y),
        v = n(86453),
        S = n.n(v),
        b = function (e) {
          let { className: t } = e;
          return (0, i.jsx)("div", {
            className: p()(S().formingPrice, t),
            children: (0, i.jsx)(o.Z, {
              type: "detail-xs-regular",
              colorToken: { color: "text-icon-primary" },
              as: "span",
              children: "Collecting data",
            }),
          });
        },
        T = n(38433),
        j = n(52042),
        w = n(35571),
        P = n(2265),
        C = n(63861);
      let D = (e) => w.i.getLatestEnhancePrices + e,
        k = new w.Z();
      var E = function (e, t) {
          var n, a;
          let i = (0, P.useCallback)(
              async () => await k.getLatestEnhancePrices(e, t),
              [e, t],
            ),
            {
              data: r,
              error: l,
              mutate: o,
              isLoading: c,
              isValidating: s,
            } = (0, C.ZP)(e ? D(e) : void 0, e ? i : null);
          return {
            starforce:
              null !== (n = null == r ? void 0 : r.starForce) && void 0 !== n
                ? n
                : [],
            prospective:
              null !== (a = null == r ? void 0 : r.prospective) && void 0 !== a
                ? a
                : [],
            latestUpdatedAt: null == r ? void 0 : r.latestUpdatedAt,
            isValidating: s,
            isLoading: c,
            mutate: o,
            error: l,
          };
        },
        I = n(12581),
        N = n.n(I),
        U = n(59914),
        R = n.n(U);
      function O(e) {
        let { style: t, content: n, children: a, className: r } = e;
        return (0, i.jsx)("div", {
          style: t,
          className: p()(R().container, r),
          children: (0, i.jsxs)("p", {
            style: {
              fontSize: "14px",
              fontWeight: 400,
              lineHeight: "140%",
              fontFamily: "inherit",
              textAlign: "center",
              width: "100%",
              color: "#69717A",
              whiteSpace: "pre-wrap",
              textWrap: "balance",
            },
            children: [
              n ||
                "Enhancement price is being calculated during the initial discovery phase, or there isn't enough data available for the selected timeframe yet.\nPlease refer to the item's tooltip and guide for more details.",
              a,
            ],
          }),
        });
      }
      var M = function (e) {
          let { className: t, id: n, style: a } = e;
          return (0, i.jsx)("div", {
            className: p()(N().section, t),
            id: n,
            style: a,
            children: (0, i.jsx)(O, {
              style: {
                color: "#69717A",
                fontSize: "14px",
                fontWeight: 400,
                lineHeight: 1.6,
                maxWidth: "500px",
                textAlign: "center",
                whiteSpace: "pre-wrap",
                textWrap: "balance",
              },
            }),
          });
        },
        L = n(65368),
        z = n(71282),
        B = n(38706);
      let F = [
        {
          header: "Enhancement Level",
          columnKey: "itemUpgrade",
          sortable: !1,
          textAlign: "left",
          render: (e) => {
            let { itemUpgrade: t } = e;
            return "".concat(t, " → ").concat(Number(t) + 1, " Star Force");
          },
        },
        {
          header: "Close Price",
          columnKey: "closePrice",
          sortable: !1,
          textAlign: "right",
          render: (e) => {
            let { closePrice: t } = e;
            return t
              ? (0, i.jsxs)("div", {
                  className: x().price,
                  children: [
                    (0, i.jsx)(m.Z, { type: "PowerCrystal", size: "large" }),
                    (0, T.p)((0, z.d)(BigInt(t), "wei")),
                  ],
                })
              : (0, i.jsx)(b, {});
          },
        },
      ];
      var G = function (e) {
          let { itemId: t } = e,
            n = (0, B.T)(),
            { starforce: a, latestUpdatedAt: r } = E(t, "0"),
            o = (0, L.Z)(),
            [c, s] = (0, P.useState)(null),
            u = new w.Z();
          (0, P.useEffect)(() => {
            !(async function () {
              try {
                let e = await u.getEnhanceLimit({ item_id: t });
                s(e);
              } catch (e) {
                console.error("getLimit 에러:", e);
              }
            })();
          }, [t]);
          let p = Array.isArray(a) ? a : [],
            m = p.length > 0,
            h = [...p].sort((e, t) => e.itemUpgrade - t.itemUpgrade),
            f = Array.from(
              { length: c && c.limit },
              (e, t) =>
                h.find((e) => e.itemUpgrade === t) || {
                  itemUpgrade: t,
                  closePrice: null,
                  itemUpgradeType: "",
                  itemUpgradeSubType: "",
                },
            ),
            y = "desktop" !== o && "qhd" !== o ? f : f.slice(0, 13),
            v = "desktop" === o || "qhd" === o ? f.slice(13, 25) : [];
          return (0, i.jsxs)(d, {
            title: "",
            className: l().pageInformationDataGap,
            children: [
              (0, i.jsx)(g, {
                latestUpdatedAt: r,
                children: n("dynamic-pricing-desc-update-info"),
              }),
              (0, i.jsx)("div", {
                className: x().tableContainer,
                children: m
                  ? (0, i.jsxs)(i.Fragment, {
                      children: [
                        y.length > 0 &&
                          (0, i.jsx)(j.Z, {
                            columns: F,
                            data: y,
                            className: x().tableContainerTable,
                            id: "b",
                          }),
                        v.length > 0 &&
                          (0, i.jsx)(j.Z, {
                            columns: F,
                            data: v,
                            className: x().tableContainerTable,
                            id: "c",
                          }),
                      ],
                    })
                  : (0, i.jsx)(M, {}),
              }),
            ],
          });
        },
        Z = n(33145),
        q = n(31365),
        H = n.n(q),
        A = function (e) {
          let { className: t, src: n } = e;
          return (0, i.jsx)("div", {
            className: p()(H().itemImage, t),
            children: (0, i.jsx)(Z.default, {
              src: n,
              alt: "",
              fetchPriority: "high",
              priority: !0,
              quality: 100,
              fill: !0,
              style: { objectFit: "contain" },
            }),
          });
        },
        Y = n(15353);
      let _ = {
          BLACK: "Black",
          RED: "Red",
          SUSPICIOUS: "Occult",
          SUSPICIOUS_ADDITIONAL: "Bonus Occult",
          ADDITIONAL: "Bonus Potential",
        },
        V = [
          {
            header: "Enhancement Type",
            columnKey: "itemUpgradeSubType",
            sortable: !1,
            textAlign: "left",
            render: (e) => {
              let { itemUpgradeSubType: t } = e;
              return (0, i.jsxs)("div", {
                style: { display: "flex", alignItems: "center", gap: "10px" },
                children: [
                  (0, i.jsx)(A, {
                    src: "".concat(Y.GW, "/images/cubes/").concat(t, ".png"),
                  }),
                  (0, i.jsxs)(o.Z, {
                    type: "body-s-regular",
                    colorToken: { color: "text-icon-primary" },
                    children: [_[t], " Cube"],
                  }),
                ],
              });
            },
          },
          {
            header: "Close Price",
            columnKey: "closePrice",
            sortable: !1,
            textAlign: "right",
            render: (e) => {
              let { closePrice: t } = e;
              return t
                ? (0, i.jsxs)("div", {
                    style: {
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: "2px",
                      alignItems: "center",
                    },
                    children: [
                      (0, i.jsx)(m.Z, { type: "PowerCrystal", size: "large" }),
                      (0, T.p)((0, z.d)(BigInt(t), "wei")),
                    ],
                  })
                : (0, i.jsx)(b, {});
            },
          },
        ];
      var J = function (e) {
          let { itemId: t } = e,
            n = (0, B.T)(),
            { prospective: a, latestUpdatedAt: r } = E("".concat(t), "0"),
            o = (0, L.Z)(),
            c = Array.isArray(a) ? a : [],
            s = [
              "SUSPICIOUS",
              "RED",
              "BLACK",
              "SUSPICIOUS_ADDITIONAL",
              "ADDITIONAL",
            ],
            u = Array.from({ length: 5 }, (e, t) => {
              let n = s[t];
              return (
                c.find((e) => e.itemUpgradeSubType === n) || {
                  itemUpgradeSubType: n,
                  closePrice: void 0,
                }
              );
            }),
            p = u.some((e) => void 0 !== e.closePrice),
            m = "desktop" !== o && "qhd" !== o ? u : u.slice(0, 3),
            h = "desktop" === o || "qhd" === o ? u.slice(3, 5) : [];
          return (0, i.jsxs)(d, {
            title: "",
            className: l().pageInformationDataGap,
            children: [
              (0, i.jsx)(g, {
                latestUpdatedAt: r,
                children: n("dynamic-pricing-desc-update-info"),
              }),
              (0, i.jsx)("div", {
                className: x().potentialTableContainer,
                children: p
                  ? (0, i.jsxs)(i.Fragment, {
                      children: [
                        m.length > 0 &&
                          (0, i.jsx)(j.Z, {
                            columns: V,
                            data: m,
                            className: x().potentialTableContainerTable,
                            fixedColumns: 1,
                          }),
                        h.length > 0 &&
                          (0, i.jsx)(j.Z, {
                            columns: V,
                            data: h,
                            className: x().potentialTableContainerTable,
                            fixedColumns: 1,
                          }),
                      ],
                    })
                  : (0, i.jsx)(M, {}),
              }),
            ],
          });
        },
        W = n(69527),
        K = n(58272),
        Q = n.n(K),
        X = n(42254),
        $ = n(70304),
        ee = n(87906);
      function et(e) {
        let { className: t } = e,
          { push: n } = (0, $.useRouter)();
        return (0, i.jsxs)("section", {
          className: p()(Q().header, t),
          children: [
            (0, i.jsx)(W.wU, {
              onClick: () => n("".concat(ee.Mg, "/").concat(ee.st)),
            }),
            (0, i.jsx)(X.Z, { className: Q().dynamicPricingSearchStyle }),
          ],
        });
      }
      let en = new w.Z(),
        ea = (e) => w.i.getItemGroupsByItemId + e;
      var ei = function (e) {
          let t = (0, P.useCallback)(
              async (e) => await en.getItemGroupByItemId(e),
              [],
            ),
            {
              data: n,
              error: a,
              isLoading: i,
              mutate: r,
              isValidating: l,
            } = (0, C.ZP)(e ? ea(e) : void 0, e ? () => t(e) : null);
          return {
            itemName: null == n ? void 0 : n.itemName,
            itemGroup: null == n ? void 0 : n.itemGroup,
            error: a,
            isLoading: i,
            mutate: r,
            isValidating: l,
          };
        },
        er = n(97747),
        el = n(48321),
        eo = n(54419),
        ec = n(82633),
        es = n(23619),
        eu = n(49171),
        ep = (e) => {
          let { data: t } = (0, eu.Z)(e),
            { push: n } = (0, $.useRouter)();
          (0, P.useEffect)(() => {
            if (t) {
              let t = encodeURIComponent(
                  JSON.stringify({
                    itemUpgradeType: "0",
                    equipType: [],
                    equipLevelType: [],
                    equipPartType: [],
                    level: [0, 200],
                  }),
                ),
                a = e ? "&searchValue=".concat(encodeURIComponent(e)) : "";
              n(
                ""
                  .concat(Y.Pz, "/gamestatus/dynamicpricing?itemGroupFilter=")
                  .concat(t)
                  .concat(a),
              );
            }
          }, [t, n, e]);
        },
        ed = n(79415),
        em = n(695),
        eh = n(30347),
        ef = n(84971),
        eg = n(68763),
        ey = n.n(eg),
        ex = function (e) {
          let { itemId: t, className: n } = e,
            { itemGroup: a, itemName: r, isLoading: l } = ei(t),
            c = (0, P.useMemo)(() => a && (0, er.P)(a), [a]),
            s = (0, L.Z)(),
            [u, d] = (0, P.useState)(!1),
            [h] = (0, es.j)(),
            f = (0, P.useRef)(null),
            [g, y] = (0, P.useState)("");
          (ep(h.searchValue),
            (0, P.useEffect)(() => {
              y(window.location.href);
              let e = (e) => {
                u && f.current && !f.current.contains(e.target) && d(!1);
              };
              return (
                document.addEventListener("mousedown", e),
                () => {
                  document.removeEventListener("mousedown", e);
                }
              );
            }, [u]));
          let x = (e) => {
              {
                let n =
                  "market" === e
                    ? ""
                        .concat(Y.T8, "/marketplace/nft?keyword=")
                        .concat(encodeURIComponent(r))
                    : "".concat(Y.T8, "/navigator/item/").concat(t);
                window.open(n, "_blank");
              }
            },
            v = (e) => {
              switch (e) {
                case "link":
                  (0, eo.z)(g).then(() => {
                    (0, ed.eS)({
                      message: "The link has been copied!",
                      duration: 3e3,
                      type: "success",
                    });
                  });
                  break;
                case "facebook":
                  (0, ec.R)(g);
                  break;
                case "twitter":
                  (0, ec.P)(g);
              }
            };
          return (0, i.jsxs)("section", {
            className: p()(ey().itemDescription, n),
            children: [
              (0, i.jsxs)("div", {
                className: ey().itemDescriptionContainer,
                children: [
                  (0, i.jsx)("div", {
                    className: ey().itemDescriptionImageContainer,
                    children: (0, i.jsx)(Z.default, {
                      src: (0, el.r)(t),
                      alt: null != r ? r : "Item Image",
                      fill: !0,
                      loading: "lazy",
                      fetchPriority: "high",
                      quality: 80,
                      style: { objectFit: "contain" },
                      unoptimized: !0,
                    }),
                  }),
                  (0, i.jsxs)("div", {
                    className: ey().itemDescriptionBox,
                    children: [
                      (0, i.jsx)(o.Z, {
                        as: "h2",
                        type:
                          "mobile" === s
                            ? "heading-xxl-bold"
                            : "display-m-bold",
                        colorToken: { color: "text-icon-primary" },
                        children: l
                          ? (0, i.jsx)(em.Z, { width: 200, height: 48 })
                          : null != r
                            ? r
                            : "---",
                      }),
                      l
                        ? (0, i.jsx)(em.Z, { width: 160, height: 22.4 })
                        : (0, i.jsx)(o.Z, {
                            as: "p",
                            type: "body-s-medium-wide",
                            colorToken: { color: "text-icon-secondary" },
                            children: c,
                          }),
                    ],
                  }),
                ],
              }),
              (0, i.jsxs)("div", {
                className: ey().itemDescriptionButtonContainer,
                children: [
                  (0, i.jsxs)("div", {
                    className: ey().itemDescriptionButtonContainerBox,
                    children: [
                      (0, i.jsxs)(eh.Z, {
                        variant: "PrimaryOutlined",
                        size: "small",
                        type: "button",
                        className: ey().itemDescriptionButtonContainerBoxButton,
                        onClick: () => x("navigator"),
                        children: [
                          "Navigator",
                          (0, i.jsx)(m.Z, { size: "small", type: "OutLink" }),
                        ],
                      }),
                      (0, i.jsxs)(eh.Z, {
                        variant: "PrimaryOutlined",
                        size: "small",
                        className: ey().itemDescriptionButtonContainerBoxButton,
                        type: "button",
                        onClick: () => x("market"),
                        children: [
                          "Marketplace",
                          (0, i.jsx)(m.Z, { size: "small", type: "OutLink" }),
                        ],
                      }),
                    ],
                  }),
                  (0, i.jsxs)("div", {
                    className: ey().itemDescriptionButtonContainerBox,
                    children: [
                      (0, i.jsx)(ef.T, {
                        style: { color: "#FC7D06" },
                        content: "Refresh",
                        children: (0, i.jsx)("button", {
                          type: "button",
                          onClick: () => {
                            t && void 0 !== window && window.location.reload();
                          },
                          className:
                            ey().itemDescriptionButtonContainerBoxCirceBtn,
                          children: (0, i.jsx)(m.Z, {
                            size: "small",
                            type: "Refresh",
                          }),
                        }),
                      }),
                      (0, i.jsxs)("div", {
                        className: ey().shareButtonWrapper,
                        ref: f,
                        children: [
                          (0, i.jsx)(ef.T, {
                            style: { color: "#FC7D06" },
                            content: "Share",
                            children: (0, i.jsx)("button", {
                              type: "button",
                              className:
                                ey().itemDescriptionButtonContainerBoxCirceBtn,
                              onClick: () => d(!u),
                              children: (0, i.jsx)(m.Z, {
                                size: "small",
                                type: "ShareFilled",
                              }),
                            }),
                          }),
                          u &&
                            (0, i.jsx)("div", {
                              className: ey().snsLinkBox,
                              children: (0, i.jsx)("ul", {
                                children: [
                                  {
                                    label: "Copy Link",
                                    type: "link",
                                    iconType: "Copy",
                                  },
                                  {
                                    label: "Share On X",
                                    type: "twitter",
                                    iconType: "SnsTwitter",
                                  },
                                  {
                                    label: "Share on Facebook",
                                    type: "facebook",
                                    iconType: "SnsFacebook",
                                  },
                                ].map((e, t) =>
                                  (0, i.jsxs)(
                                    "li",
                                    {
                                      onClick: () => v(e.type),
                                      children: [
                                        (0, i.jsx)(m.Z, {
                                          type: e.iconType,
                                          size: "small",
                                        }),
                                        (0, i.jsx)(o.Z, {
                                          type: "body-s-regular",
                                          as: "span",
                                          children: e.label,
                                        }),
                                      ],
                                    },
                                    t,
                                  ),
                                ),
                              }),
                            }),
                        ],
                      }),
                    ],
                  }),
                ],
              }),
            ],
          });
        },
        ev = function (e) {
          let { itemId: t } = e;
          return (0, i.jsxs)("article", {
            className: l().pageContainer,
            children: [
              (0, i.jsx)(et, { className: l().pageHeader }),
              (0, i.jsx)(ex, {
                className: l().pageDescriptionMargin,
                itemId: t,
              }),
            ],
          });
        },
        eS = n(37069),
        eb =
          ("object" == typeof localStorage &&
            (localStorage.getItem("debug")?.includes("next-usequerystate") ||
              localStorage.getItem("debug")?.includes("nuqs"))) ||
          !1;
      function eT(e, ...t) {
        if (!eb) return;
        let n = (function (e, ...t) {
          return e.replace(/%[sfdO]/g, (e) => {
            let n = t.shift();
            return "%O" === e && n
              ? JSON.stringify(n).replace(/"([^"]+)":/g, "$1:")
              : String(n);
          });
        })(e, ...t);
        (performance.mark(n), console.log(e, ...t));
      }
      function ej(e, t, n) {
        try {
          return e(t);
        } catch (e) {
          return (
            !(function (e, ...t) {
              eb && console.warn(e, ...t);
            })(
              "[nuqs] Error while parsing value `%s`: %O" +
                (n ? " (for key `%s`)" : ""),
              t,
              e,
              n,
            ),
            null
          );
        }
      }
      function ew(e) {
        function t(t) {
          if (void 0 === t) return null;
          let n = "";
          if (Array.isArray(t)) {
            if (void 0 === t[0]) return null;
            n = t[0];
          }
          return ("string" == typeof t && (n = t), ej(e.parse, n));
        }
        return {
          ...e,
          parseServerSide: t,
          withDefault(e) {
            return {
              ...this,
              defaultValue: e,
              parseServerSide: (n) => t(n) ?? e,
            };
          },
          withOptions(e) {
            return { ...this, ...e };
          },
        };
      }
      ew({ parse: (e) => e, serialize: (e) => `${e}` });
      var eP = ew({
        parse: (e) => {
          let t = parseInt(e);
          return Number.isNaN(t) ? null : t;
        },
        serialize: (e) => Math.round(e).toFixed(),
      });
      function eC(e) {
        return ew({
          parse: (t) => (e.includes(t) ? t : null),
          serialize: (e) => e.toString(),
        });
      }
      (ew({
        parse: (e) => {
          let t = parseInt(e, 16);
          return Number.isNaN(t) ? null : t;
        },
        serialize: (e) => {
          let t = Math.round(e).toString(16);
          return t.padStart(t.length + (t.length % 2), "0");
        },
      }),
        ew({
          parse: (e) => {
            let t = parseFloat(e);
            return Number.isNaN(t) ? null : t;
          },
          serialize: (e) => e.toString(),
        }),
        ew({
          parse: (e) => "true" === e,
          serialize: (e) => (e ? "true" : "false"),
        }),
        ew({
          parse: (e) => {
            let t = parseInt(e);
            return Number.isNaN(t) ? null : new Date(t);
          },
          serialize: (e) => e.valueOf().toString(),
        }),
        ew({
          parse: (e) => {
            let t = new Date(e);
            return Number.isNaN(t.valueOf()) ? null : t;
          },
          serialize: (e) => e.toISOString(),
        }));
      var eD = {
        409: "Multiple versions of the library are loaded. This may lead to unexpected behavior. Currently using `%s`, but `%s` was about to load on top.",
        429: "URL update rate-limited by the browser. Consider increasing `throttleMs` for key(s) `%s`. %O",
        500: "Empty search params cache. Search params can't be accessed in Layouts.",
        501: "Search params cache already populated. Have you called `parse` twice?",
      };
      function ek(e) {
        return `[nuqs] ${eD[e]}
  See https://err.47ng.com/NUQS-${e}`;
      }
      var eE = n(64138),
        eI = (function () {
          if ("undefined" == typeof window || !window.GestureEvent) return 50;
          try {
            let e = navigator.userAgent?.match(/version\/([\d\.]+) safari/i);
            return parseFloat(e[1]) >= 17 ? 120 : 320;
          } catch {
            return 320;
          }
        })(),
        eN = new Map(),
        eU = { history: "replace", scroll: !1, shallow: !0, throttleMs: eI },
        eR = new Set(),
        eO = 0,
        eM = null;
      function eL(e, t, n, a) {
        let i = null === t ? null : n(t);
        (eT("[nuqs queue] Enqueueing %s=%s %O", e, i, a),
          eN.set(e, i),
          "push" === a.history && (eU.history = "push"),
          a.scroll && (eU.scroll = !0),
          !1 === a.shallow && (eU.shallow = !1),
          a.startTransition && (eR.add(a.startTransition), (eU.shallow = !1)),
          (eU.throttleMs = Math.max(
            a.throttleMs ?? eI,
            Number.isFinite(eU.throttleMs) ? eU.throttleMs : 0,
          )));
      }
      function ez(e) {
        return eN.get(e) ?? null;
      }
      function eB(e) {
        return (
          null === eM &&
            (eM = new Promise((t, n) => {
              if (!Number.isFinite(eU.throttleMs)) {
                (eT("[nuqs queue] Skipping flush due to throttleMs=Infinity"),
                  t(new URLSearchParams(location.search)),
                  setTimeout(() => {
                    eM = null;
                  }, 0));
                return;
              }
              function a() {
                eO = performance.now();
                let [a, i] = (function (e) {
                  let t = new URLSearchParams(location.search);
                  if (0 === eN.size) return [t, null];
                  let n = Array.from(eN.entries()),
                    a = { ...eU },
                    i = Array.from(eR);
                  for (let [e, i] of (eN.clear(),
                  eR.clear(),
                  (eU.history = "replace"),
                  (eU.scroll = !1),
                  (eU.shallow = !0),
                  (eU.throttleMs = eI),
                  eT("[nuqs queue] Flushing queue %O with options %O", n, a),
                  n))
                    null === i ? t.delete(e) : t.set(e, i);
                  try {
                    let n = window.next?.router;
                    if ("string" == typeof n?.state?.asPath) {
                      let e = eF(n.state.asPath.split("?")[0] ?? "", t);
                      (eT("[nuqs queue (pages)] Updating url: %s", e),
                        ("push" === a.history ? n.push : n.replace).call(
                          n,
                          e,
                          e,
                          { scroll: a.scroll, shallow: a.shallow },
                        ));
                    } else {
                      let n = eF(location.origin + location.pathname, t);
                      eT("[nuqs queue (app)] Updating url: %s", n);
                      let r =
                          "push" === a.history
                            ? history.pushState
                            : history.replaceState,
                        l =
                          (window.next?.version ?? "") >= "14.1.0"
                            ? null
                            : history.state;
                      (r.call(history, l, eZ, n),
                        a.scroll && window.scrollTo(0, 0),
                        a.shallow ||
                          (function (e, t) {
                            let n = (a) => {
                              if (a === e.length) return t();
                              let i = e[a];
                              if (!i)
                                throw Error("Invalid transition function");
                              i(() => n(a + 1));
                            };
                            n(0);
                          })(i, () => {
                            e.replace(n, { scroll: !1 });
                          }));
                    }
                    return [t, null];
                  } catch (e) {
                    return (
                      console.error(ek(429), n.map(([e]) => e).join(), e),
                      [t, e]
                    );
                  }
                })(e);
                (null === i ? t(a) : n(a), (eM = null));
              }
              setTimeout(function () {
                let e = performance.now() - eO,
                  t = eU.throttleMs,
                  n = Math.max(0, Math.min(t, t - e));
                (eT(
                  "[nuqs queue] Scheduling flush in %f ms. Throttled at %f ms",
                  n,
                  t,
                ),
                  0 === n ? a() : setTimeout(a, n));
              }, 0);
            })),
          eM
        );
      }
      function eF(e, t) {
        return (
          (e.split("#")[0] ?? "") +
          (function (e) {
            if (0 === e.size) return "";
            let t = [];
            for (let [n, a] of e.entries())
              t.push(
                `${n}=${a.replace(/%/g, "%25").replace(/\+/g, "%2B").replace(/ /g, "+").replace(/#/g, "%23").replace(/&/g, "%26").replace(/"/g, "%22").replace(/'/g, "%27").replace(/`/g, "%60").replace(/</g, "%3C").replace(/>/g, "%3E")}`,
              );
            return "?" + t.join("&");
          })(t) +
          location.hash
        );
      }
      var eG = Symbol("__nuqs__SYNC__"),
        eZ = "__nuqs__NO_SYNC__",
        eq = Symbol("__nuqs__NOTIFY__"),
        eH = (0, eE.Z)();
      function eA(
        e,
        {
          history: t = "replace",
          shallow: n = !0,
          scroll: a = !1,
          throttleMs: i = eI,
          parse: r = (e) => e,
          serialize: l = String,
          defaultValue: o,
          clearOnDefault: c = !1,
          startTransition: s,
        } = {
          history: "replace",
          scroll: !1,
          shallow: !0,
          throttleMs: eI,
          parse: (e) => e,
          serialize: String,
          clearOnDefault: !1,
          defaultValue: void 0,
        },
      ) {
        let u = (0, $.useRouter)(),
          p = (0, $.useSearchParams)(),
          [d, m] = P.useState(() => {
            let t = ez(e),
              n =
                "object" != typeof location
                  ? (p?.get(e) ?? null)
                  : (new URLSearchParams(location.search).get(e) ?? null),
              a = t ?? n;
            return null === a ? null : ej(r, a, e);
          }),
          h = P.useRef(d);
        (eT("[nuqs `%s`] render - state: %O, iSP: %s", e, d, p?.get(e) ?? null),
          P.useEffect(() => {
            if (window.next?.version !== "14.0.3") return;
            let t = p.get(e) ?? null,
              n = null === t ? null : ej(r, t, e);
            (eT("[nuqs `%s`] syncFromUseSearchParams %O", e, n),
              (h.current = n),
              m(n));
          }, [p?.get(e), e]),
          P.useInsertionEffect(() => {
            function t(t) {
              (eT("[nuqs `%s`] updateInternalState %O", e, t),
                (h.current = t),
                m(t));
            }
            function n(n) {
              let a = n.get(e) ?? null,
                i = null === a ? null : ej(r, a, e);
              (eT("[nuqs `%s`] syncFromURL %O", e, i), t(i));
            }
            return (
              eT("[nuqs `%s`] subscribing to sync", e),
              eH.on(eG, n),
              eH.on(e, t),
              () => {
                (eT("[nuqs `%s`] unsubscribing from sync", e),
                  eH.off(eG, n),
                  eH.off(e, t));
              }
            );
          }, [e]));
        let f = P.useCallback(
          (r, p = {}) => {
            let d = "function" == typeof r ? r(h.current ?? o ?? null) : r;
            return (
              (p.clearOnDefault || c) && d === o && (d = null),
              eH.emit(e, d),
              eL(e, d, l, {
                history: p.history ?? t,
                shallow: p.shallow ?? n,
                scroll: p.scroll ?? a,
                throttleMs: p.throttleMs ?? i,
                startTransition: p.startTransition ?? s,
              }),
              eB(u)
            );
          },
          [e, t, n, a, i, s],
        );
        return [d ?? o ?? null, f];
      }
      function eY(e, t) {
        return Object.keys(e).reduce((n, a) => {
          let { defaultValue: i, parse: r } = e[a],
            l = t?.get(a) ?? null,
            o = ez(a) ?? l,
            c = null === o ? null : ej(r, o, a);
          return ((n[a] = c ?? i ?? null), n);
        }, {});
      }
      "object" == typeof history &&
        (function () {
          let e = "1.17.0",
            t = history.__nuqs_patched;
          if (t) {
            t !== e && console.error(ek(409), t, e);
            return;
          }
          for (let t of (eT("[nuqs] Patching history with %s", e),
          ["pushState", "replaceState"])) {
            let e = history[t].bind(history);
            history[t] = function (n, a, i) {
              if (!i)
                return (
                  eT("[nuqs] history.%s(null) (%s) %O", t, a, n),
                  e(n, a, i)
                );
              let r = a === eZ ? "internal" : "external",
                l = new URL(i, location.origin).searchParams;
              if (
                (eT("[nuqs] history.%s(%s) (%s) %O", t, i, r, n),
                "external" === r)
              ) {
                for (let [e, t] of l.entries()) {
                  let n = ez(e);
                  null !== n &&
                    n !== t &&
                    (eT(
                      "[nuqs] Overwrite detected for key: %s, Server: %s, queue: %s",
                      e,
                      t,
                      n,
                    ),
                    l.set(e, n));
                }
                setTimeout(() => {
                  (eT(
                    "[nuqs] External history.%s call: triggering sync with %s",
                    t,
                    l,
                  ),
                    eH.emit(eG, l),
                    eH.emit(eq, { search: l, source: r }));
                }, 0);
              } else
                setTimeout(() => {
                  eH.emit(eq, { search: l, source: r });
                }, 0);
              return e(n, a === eZ ? "" : a, i);
            };
          }
          Object.defineProperty(history, "__nuqs_patched", {
            value: e,
            writable: !1,
            enumerable: !1,
            configurable: !1,
          });
        })();
      var e_ = n(71096),
        eV = n.n(e_),
        eJ = n(65801);
      let eW = eV()().unix() + 2e3,
        eK = {
          timePeriodType: eC(["0", "1", "2", "3", "4", "5"]).withDefault("1"),
          minTimestamp: eP.withDefault(0),
          maxTimestamp: eP.withDefault(eW),
          itemUpgrade:
            ((a = [
              0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
              19, 20, 21, 22, 23, 24, 25,
            ]),
            ew({
              parse: (e) => {
                let t = parseFloat(e);
                return a.includes(t) ? t : null;
              },
              serialize: (e) => e.toString(),
            })),
          itemUpgradeType: eC(["0", "1"]),
          itemUpgradeSubType: eC([
            "0",
            "2711000",
            "2730000",
            "5062010",
            "5062009",
            "5062500",
          ]),
        };
      var eQ = function () {
          var e;
          let t = (function (
            e,
            {
              history: t = "replace",
              scroll: n = !1,
              shallow: a = !0,
              throttleMs: i = eI,
              clearOnDefault: r = !1,
              startTransition: l,
            } = {},
          ) {
            let o = Object.keys(e).join(","),
              c = (0, $.useRouter)(),
              s = (0, $.useSearchParams)(),
              [u, p] = P.useState(() =>
                "object" != typeof location
                  ? eY(e, s ?? new URLSearchParams())
                  : eY(e, new URLSearchParams(location.search)),
              ),
              d = P.useRef(u);
            return (
              eT("[nuq+ `%s`] render - state: %O, iSP: %s", o, u, s),
              P.useInsertionEffect(() => {
                function t(e) {
                  (eT("[nuq+ `%s`] updateInternalState %O", o, e),
                    (d.current = e),
                    p(e));
                }
                function n(n) {
                  let a = eY(e, n);
                  (eT("[nuq+ `%s`] syncFromURL %O", o, a), t(a));
                }
                let a = Object.keys(e).reduce(
                  (n, a) => (
                    (n[a] = (n) => {
                      let { defaultValue: i } = e[a];
                      ((d.current = { ...d.current, [a]: n ?? i ?? null }),
                        eT(
                          "[nuq+ `%s`] Cross-hook key sync %s: %O (default: %O). Resolved: %O",
                          o,
                          a,
                          n,
                          i,
                          d.current,
                        ),
                        t(d.current));
                    }),
                    n
                  ),
                  {},
                );
                for (let t of (eH.on(eG, n), Object.keys(e)))
                  (eT("[nuq+ `%s`] Subscribing to sync for `%s`", o, t),
                    eH.on(t, a[t]));
                return () => {
                  for (let t of (eH.off(eG, n), Object.keys(e)))
                    (eT("[nuq+ `%s`] Unsubscribing to sync for `%s`", o, t),
                      eH.off(t, a[t]));
                };
              }, [e]),
              [
                u,
                P.useCallback(
                  (s, u = {}) => {
                    let p = "function" == typeof s ? s(d.current) : s;
                    for (let [c, s] of (eT("[nuq+ `%s`] setState: %O", o, p),
                    Object.entries(p))) {
                      let o = e[c];
                      o &&
                        ((u.clearOnDefault || r) &&
                          s === o.defaultValue &&
                          (s = null),
                        eH.emit(c, s),
                        eL(c, s, o.serialize ?? String, {
                          history: u.history ?? t,
                          shallow: u.shallow ?? a,
                          scroll: u.scroll ?? n,
                          throttleMs: u.throttleMs ?? i,
                          startTransition: u.startTransition ?? l,
                        }));
                    }
                    return eB(c);
                  },
                  [e, t, a, n, i, l],
                ),
              ]
            );
          })(eK);
          return {
            ...((null == t ? void 0 : t[0]) || {}),
            minTimestamp: (function (e, t) {
              let n;
              let a = new Date(1e3 * e);
              switch (t) {
                case "1":
                case "2":
                case "3":
                  n = eJ.timeDay.offset(a, -20);
                  break;
                case "4":
                  n = eJ.timeWeek.offset(a, -12);
                  break;
                case "5":
                  n = eJ.timeYear.offset(a, -1);
                  break;
                default:
                  n = eJ.timeHour.offset(a, -12);
              }
              return Math.floor(n.getTime() / 1e3);
            })(
              eW,
              (null === (e = t[0]) || void 0 === e
                ? void 0
                : e.timePeriodType) || "1",
            ),
            maxTimestamp: eW,
          };
        },
        eX = (e) => {
          let [t, n] = (0, P.useState)({ width: 0, height: 0 }),
            a = (0, P.useRef)(null),
            i = e || a;
          return (
            (0, P.useEffect)(() => {
              if (!i.current) return;
              let e = i.current,
                t = new ResizeObserver((e) => {
                  let t = e[0];
                  if (t.contentBoxSize) {
                    let e = Array.isArray(t.contentBoxSize)
                      ? t.contentBoxSize[0]
                      : t.contentBoxSize;
                    n({ width: e.inlineSize, height: e.blockSize });
                  } else
                    n({
                      width: t.contentRect.width,
                      height: t.contentRect.height,
                    });
                });
              return (
                e && t.observe(e),
                () => {
                  (e && t.unobserve(e), t.disconnect());
                }
              );
            }, [i]),
            t
          );
        };
      let e$ = "custom_chart";
      var e0 = n(14229),
        e1 = n.n(e0);
      let e2 = [
        { value: "2711000", label: "Ocult Cube", name: "itemUpgradeSubType" },
        { value: "5062009", label: "Red Cube", name: "itemUpgradeSubType" },
        { value: "5062010", label: "Black Cube", name: "itemUpgradeSubType" },
        {
          value: "2730000",
          label: "Bonus Ocult Cube",
          name: "itemUpgradeSubType",
        },
        {
          value: "5062500",
          label: "Bonus Potential Cube",
          name: "itemUpgradeSubType",
        },
      ];
      n(72260);
      let e4 = (0, P.memo)(
        ({
          label: e,
          className: t,
          onClick: n,
          icon: a,
          iconAlign: r,
          disabled: l,
          style: o,
          children: c,
          ...s
        }) =>
          (0, i.jsxs)("div", {
            ...s,
            "aria-disabled": l,
            className: u("chip", "_chip_1uibd_9", t),
            style: { ...o, ...(n ? { cursor: "pointer" } : {}) },
            onClick: l ? void 0 : n,
            children: [
              "left" === r && a,
              (0, i.jsx)("span", {
                className: "_chipText_1uibd_36",
                children: e || c,
              }),
              "right" === r && a,
            ],
          }),
      );
      n(12063);
      let e3 = {
          chip: "_chip_1jd2u_9",
          selected: "_selected_1jd2u_9",
          accent: "_accent_1jd2u_9",
          primary: "_primary_1jd2u_19",
          filled: "_filled_1jd2u_29",
          outlined: "_outlined_1jd2u_46",
          ghost: "_ghost_1jd2u_63",
          dropdown: "_dropdown_1jd2u_81",
          chipIcon: "_chipIcon_1jd2u_91",
        },
        e5 = (0, P.memo)(
          ({
            className: e,
            variants: t,
            selected: n,
            children: a,
            dropdown: r,
            iconAlign: l,
            icon: o,
            ...c
          }) =>
            (0, i.jsx)(e4, {
              ...c,
              className: u(
                e3.chip,
                e3[(null == t ? void 0 : t.style) || "filled"],
                e3[(null == t ? void 0 : t.color) || "accent"],
                { [`selected ${e3.selected}`]: n, [e3.dropdown]: r },
                e,
              ),
              icon: r
                ? (0, i.jsx)(m.Z, {
                    type: "CaretDown",
                    width: 14,
                    height: 14,
                    className: e3.chipIcon,
                  })
                : o,
              iconAlign: r ? "right" : l,
              children: a,
            }),
        );
      var e6 = (e, t) => {
          (0, P.useEffect)(() => {
            let n = (n) => {
              var a;
              !e.current ||
                (null === (a = e.current) || void 0 === a
                  ? void 0
                  : a.contains(n.target)) ||
                null == t ||
                t(n);
            };
            return (
              document.addEventListener("click", n),
              () => {
                document.removeEventListener("click", n);
              }
            );
          }, [t, e]);
        },
        e9 = n(833),
        e8 = n.n(e9),
        e7 = n(3357),
        te = n.n(e7);
      let tt = (0, i.jsx)("svg", {
          xmlns: "http://www.w3.org/2000/svg",
          width: "16",
          height: "16",
          viewBox: "0 0 16 16",
          fill: "none",
          children: (0, i.jsx)("path", {
            d: "M5 4.5L11 8L5 11.5V4.5Z",
            fill: "currentColor",
          }),
        }),
        tn = (function () {
          let e = [];
          for (let t = 0; t <= 24; t++) {
            let n = {
              value: "".concat(t),
              label: (0, i.jsxs)("span", {
                className: e8().optionLabel,
                children: [t, tt, t + 1],
              }),
              name: "itemUpgrade",
            };
            e.push(n);
          }
          return e;
        })(),
        ta = (0, P.forwardRef)((e, t) => {
          let {
            className: n,
            onClick: a,
            value: r,
            limit: l = 25,
            data: o = [],
          } = e;
          return (0, i.jsx)("div", {
            ref: t,
            className: p()(e8().optionsContainerStyle, n),
            children: o.map((e, t) => {
              if (t + 1 > l) return;
              let n = p()(
                e8().optionButtonStyle,
                r === e.value && e8().optionButtonActive,
              );
              return (0, i.jsx)(
                "button",
                {
                  type: "button",
                  className: n,
                  onClick: () => a(e.value),
                  children: e.label,
                },
                "".concat(e.value) + t,
              );
            }),
          });
        });
      var ti = function (e) {
          var t;
          let { limit: n = 25, enhanceType: a = [] } = e,
            [r, l] = (0, P.useState)(null),
            [o, c] = eA("itemUpgradeType", {
              defaultValue: a.includes("starforce") ? "0" : "1",
            }),
            [s, u] = eA("itemUpgradeSubType", {
              defaultValue: "0" === o ? "0" : e2[0].value,
            }),
            [d, h] = eA("itemUpgrade"),
            f = (0, P.useRef)(null);
          (e6(
            f,
            (0, P.useCallback)(() => {
              null !== r && l(null);
            }, [r]),
          ),
            (0, P.useEffect)(() => {
              a.includes("starforce") && !o && (h("0"), c("0"));
            }, [a, o, h, c]));
          let g = a.reduce(
              (e, t) => (
                "starforce" === t
                  ? e.push({
                      value: "0",
                      label: "Star Force",
                      name: "itemUpgradeType",
                    })
                  : "potential" === t &&
                    e.push({
                      value: "1",
                      label: "Potential",
                      name: "itemUpgradeType",
                    }),
                e
              ),
              [],
            ),
            y = (0, P.useCallback)(
              (e) => {
                "itemUpgradeType" === r && "0" === e
                  ? l("itemUpgrade")
                  : "itemUpgradeType" === r && "1" === e
                    ? l("itemUpgradeSubType")
                    : ("itemUpgrade" === r || "itemUpgradeSubType" === r) &&
                      l(null);
              },
              [r],
            );
          return (0, i.jsxs)("div", {
            children: [
              (0, i.jsxs)("div", {
                className: e8().mobileOptionSelectBtnContainerStyle,
                children: [
                  a.length > 0
                    ? (0, i.jsxs)("button", {
                        className: p()(
                          e8().mobileOptionSelectButtonStyle,
                          "itemUpgradeType" === r && e8().activeBlueColor,
                          te().selectChip,
                          te().outlined,
                        ),
                        type: "button",
                        onClick: (e) => {
                          (e.preventDefault(),
                            l(
                              "itemUpgradeType" === r
                                ? null
                                : "itemUpgradeType",
                            ));
                        },
                        children: [
                          "0" == o ? "Star Force" : "Potential",
                          (0, i.jsx)("span", {
                            children:
                              "itemUpgradeType" === r
                                ? (0, i.jsx)(m.Z, {
                                    size: "medium",
                                    type: "CaretUp",
                                  })
                                : (0, i.jsx)(m.Z, {
                                    size: "medium",
                                    type: "CaretDown",
                                  }),
                          }),
                        ],
                      })
                    : void 0,
                  a.length > 0
                    ? (0, i.jsxs)("button", {
                        className: p()(
                          e8().mobileOptionSelectButtonStyle,
                          ("itemUpgradeSubType" === r || "itemUpgrade" === r) &&
                            e8().activeBlueColor,
                          te().selectChip,
                          te().outlined,
                        ),
                        type: "button",
                        onClick: (e) => {
                          (e.preventDefault(),
                            l(
                              "itemUpgradeSubType" === r || "itemUpgrade" === r
                                ? null
                                : "0" === o
                                  ? "itemUpgrade"
                                  : "1" === o
                                    ? "itemUpgradeSubType"
                                    : null,
                            ));
                        },
                        children: [
                          (0, i.jsx)("span", {
                            className: e8().enhancementInfoStyle,
                            children:
                              "0" === o
                                ? (0, i.jsxs)(i.Fragment, {
                                    children: [
                                      d || 0,
                                      (0, i.jsx)(m.Z, {
                                        size: "small",
                                        type: "ArrowRight",
                                      }),
                                      Number(d) + 1,
                                      " Star Force",
                                    ],
                                  })
                                : "1" === o
                                  ? (null == e2
                                      ? void 0
                                      : null ===
                                            (t = e2.find(
                                              (e) => e.value === s,
                                            )) || void 0 === t
                                        ? void 0
                                        : t.label) || e2[0].label
                                  : null,
                          }),
                          (0, i.jsx)("span", {
                            children:
                              "itemUpgradeSubType" === r || "itemUpgrade" === r
                                ? (0, i.jsx)(m.Z, {
                                    size: "medium",
                                    type: "CaretUp",
                                  })
                                : (0, i.jsx)(m.Z, {
                                    size: "medium",
                                    type: "CaretDown",
                                  }),
                          }),
                        ],
                      })
                    : void 0,
                ],
              }),
              "itemUpgradeType" === r &&
                (0, i.jsx)(ta, {
                  ref: f,
                  onClick: (e) => {
                    ("0" === e ? u("") : h(""), y(e), c(e));
                  },
                  limit: n,
                  value: o || "0",
                  data: g,
                  className: e8().upgradeTypeDropdownStyle,
                }),
              "itemUpgrade" === r &&
                (0, i.jsx)(ta, {
                  ref: f,
                  onClick: (e) => {
                    (y(e), h(e), u(""));
                  },
                  value: d || "0",
                  limit: n,
                  data: tn,
                  className: e8().gridRepeat3Style,
                }),
              "itemUpgradeSubType" === r &&
                (0, i.jsx)(ta, {
                  ref: f,
                  onClick: (e) => {
                    (y(e), u(e), h(""));
                  },
                  value: s || e2[0].value,
                  limit: n,
                  data: e2,
                  className: e8().gridRepeat2Style,
                }),
            ],
          });
        },
        tr = (e) =>
          (0, i.jsxs)("svg", {
            width: "16",
            height: "16",
            viewBox: "0 0 16 16",
            fill: "none",
            xmlns: "http://www.w3.org/2000/svg",
            xmlnsXlink: "http://www.w3.org/1999/xlink",
            ...e,
            children: [
              (0, i.jsx)("rect", {
                width: "16",
                height: "16",
                fill: "url(#pattern0)",
              }),
              (0, i.jsxs)("defs", {
                children: [
                  (0, i.jsx)("pattern", {
                    id: "pattern0",
                    patternContentUnits: "objectBoundingBox",
                    width: "1",
                    height: "1",
                    children: (0, i.jsx)("use", {
                      xlinkHref: "#image0_556_3210",
                      transform: "scale(0.0116279)",
                    }),
                  }),
                  (0, i.jsx)("image", {
                    id: "image0_556_3210",
                    width: "86",
                    height: "86",
                    xlinkHref:
                      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAABWCAYAAABVVmH3AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAylpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDkuMS1jMDAxIDc5LjE0NjI4OTk3NzcsIDIwMjMvMDYvMjUtMjM6NTc6MTQgICAgICAgICI+IDxyZGY6UkRGIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyI+IDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bXA6Q3JlYXRvclRvb2w9IkFkb2JlIFBob3Rvc2hvcCAyNS4wIChNYWNpbnRvc2gpIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjY0RjRDMDAzNjk5MTExRUVCM0JFQUU0RDk3RkMxODVEIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOjY0RjRDMDA0Njk5MTExRUVCM0JFQUU0RDk3RkMxODVEIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6NjRGNEMwMDE2OTkxMTFFRUIzQkVBRTREOTdGQzE4NUQiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NjRGNEMwMDI2OTkxMTFFRUIzQkVBRTREOTdGQzE4NUQiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz5168uuAABAaUlEQVR4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",
                  }),
                ],
              }),
            ],
          }),
        tl = n(4455),
        to = n.n(tl);
      function tc(e) {
        let { value: t, className: n, icon: a } = e,
          { integer: r, decimal: l } = (function (e) {
            var t;
            if (0 !== e && !e) return { integer: "", decimal: null };
            let n = e.toString().split("."),
              a = n[0],
              i = null !== (t = n[1]) && void 0 !== t ? t : "";
            for (; i.length < 6; ) i += "0";
            return { integer: a, decimal: i.split("") };
          })(t),
          o =
            null == l
              ? void 0
              : l.map((e, t) => {
                  if ("0" !== e) return !1;
                  for (
                    let e = t + 1;
                    e < ((null == l ? void 0 : l.length) || 0);
                    e++
                  )
                    if ((null == l ? void 0 : l[e]) !== "0") return !1;
                  return !0;
                }),
          c =
            null == l
              ? void 0
              : l.map((e, t) =>
                  (0, i.jsx)(
                    "span",
                    {
                      className: p()(
                        n,
                        to().decimalPriceDecimalValue,
                        !!o &&
                          o.length > t &&
                          (null == o ? void 0 : o[t]) &&
                          to().zeroPaddingStyle,
                      ),
                      children: e,
                    },
                    t,
                  ),
                );
        return (0, i.jsxs)("div", {
          className: p()(to().decimalPriceComponentStyle),
          children: [
            a || (0, i.jsx)(tr, { className: to().powerIconStyle }),
            (0, i.jsxs)("div", {
              className: p()(n, to().decimalPriceValue),
              children: [
                r ? (0, T.p)(r) : "---",
                l &&
                  (0, i.jsx)("span", {
                    className: to().decimalDotStyle,
                    children: ".",
                  }),
                c,
              ],
            }),
          ],
        });
      }
      var ts = n(73719),
        tu = n.n(ts);
      let tp = [
        { label: "20m", value: "1" },
        { label: "1H", value: "2" },
        { label: "1D", value: "3" },
        { label: "1W", value: "4" },
        { label: "1M", value: "5" },
      ];
      var td = (e) => {
        let {
          maxPrice: t,
          minPrice: n,
          endPrice: a,
          totalEnhancementCount: r,
          enhanceType: l,
          timePeriodType: o,
          setTimePeriodType: c,
          currentLimit: s,
          tooltipZIndex: u = 2,
        } = e;
        return (0, i.jsx)("section", {
          children: (0, i.jsxs)("section", {
            style: { position: "relative" },
            children: [
              (0, i.jsxs)("div", {
                className: tu().timePeriodButtonContainerStyle,
                children: [
                  (0, i.jsx)(ti, { limit: s, enhanceType: l }),
                  (0, i.jsx)("div", {
                    className: tu().chipWrap,
                    children:
                      null == tp
                        ? void 0
                        : tp.map((e) =>
                            (0, i.jsx)(
                              e5,
                              {
                                variants: { style: "filled", color: "accent" },
                                selected: o === e.value,
                                onClick: () => {
                                  c(e.value);
                                },
                                label: e.label,
                              },
                              e.value,
                            ),
                          ),
                  }),
                ],
              }),
              (0, i.jsxs)("div", {
                className: tu().priceDescriptionContainerStyle,
                children: [
                  (0, i.jsx)("dl", {
                    className: tu().closePriceDescriptionDatalistStyle,
                    children: (0, i.jsxs)(P.Suspense, {
                      children: [
                        (0, i.jsxs)("dt", {
                          className: tu().priceDescriptionPriceTextStyle,
                          children: [
                            "Close Price",
                            (0, i.jsx)(ef.T, {
                              zIndex: u,
                              content:
                                "Rather than reflecting the price paid for enhancement like other metrics, ‘Close Price’ indicates the final price of an item’s enhancement within a set period.\nAs a consequence, it may rise above the highest price or fall below the lowest price",
                              variants: { color: "black75" },
                              children: (0, i.jsx)(m.Z, {
                                type: "HelpFilled",
                                size: "medium",
                              }),
                            }),
                          ],
                        }),
                        (0, i.jsx)("dd", {
                          className: tu().priceDescriptionPriceValueStyle,
                          children: (0, i.jsx)(tc, { value: a }),
                        }),
                      ],
                    }),
                  }),
                  (0, i.jsxs)("dl", {
                    className: tu().rangePriceDescriptionDatalistStyle,
                    children: [
                      (0, i.jsx)(P.Suspense, {
                        children: (0, i.jsxs)("div", {
                          className: tu().rangePriceDescriptionDatalistBoxStyle,
                          children: [
                            (0, i.jsx)("dt", {
                              className: p()(
                                tu().priceDescriptionPriceTextStyle,
                                tu().minMaxColorStyle,
                              ),
                              children: "Lowest Price",
                            }),
                            (0, i.jsx)("dd", {
                              className: p()(
                                tu().priceDescriptionPriceValueStyle,
                                tu().minMaxColorStyle,
                              ),
                              children: (0, i.jsx)(tc, { value: n }),
                            }),
                          ],
                        }),
                      }),
                      (0, i.jsx)("div", { children: "~" }),
                      (0, i.jsx)(P.Suspense, {
                        children: (0, i.jsxs)("div", {
                          className: tu().rangePriceDescriptionDatalistBoxStyle,
                          children: [
                            (0, i.jsx)("dt", {
                              className: p()(
                                tu().priceDescriptionPriceTextStyle,
                                tu().minMaxColorStyle,
                              ),
                              children: "Highest Price",
                            }),
                            (0, i.jsx)("dd", {
                              className: p()(
                                tu().priceDescriptionPriceValueStyle,
                                tu().minMaxColorStyle,
                              ),
                              children: (0, i.jsx)(tc, { value: t }),
                            }),
                          ],
                        }),
                      }),
                    ],
                  }),
                  (0, i.jsx)("dl", {
                    className: tu().enhanceDescriptionDatalistStyle,
                    children: (0, i.jsxs)(P.Suspense, {
                      children: [
                        (0, i.jsx)("dt", {
                          className: p()(
                            tu().priceDescriptionPriceTextStyle,
                            tu().enhancementColorStyle,
                          ),
                          children: "Enhancement Count",
                        }),
                        (0, i.jsx)("dd", {
                          className: p()(
                            tu().priceDescriptionPriceValueStyle,
                            tu().enhancementColorStyle,
                          ),
                          children: r ? (0, T.p)(r) : "---",
                        }),
                      ],
                    }),
                  }),
                ],
              }),
            ],
          }),
        });
      };
      let tm = (e) => {
        let [t, n] = (0, P.useState)(!0),
          [a, i] = eA("timePeriodType", { scroll: !1, parse: (e) => e }),
          [r, l] = (0, P.useState)([]),
          [o, c] = (0, P.useState)(25),
          s = (0, P.useCallback)(
            (e) => {
              i(e);
            },
            [i],
          );
        return (
          (0, P.useEffect)(() => {
            e &&
              (async () => {
                try {
                  n(!0);
                  let t = new w.Z(),
                    [a, i] = await Promise.all([
                      t.getEnhanceType(e),
                      t.getEnhanceLimit({ item_id: e }),
                    ]),
                    r = [];
                  (a.isStarForce && r.push("starforce"),
                    a.isProspective && r.push("potential"),
                    c((null == i ? void 0 : i.limit) || 0),
                    l(r),
                    n(!1));
                } catch (e) {
                  (n(!1), console.error(e));
                }
              })();
          }, [e, s]),
          {
            timePeriodType: a,
            enhanceType: r,
            currentLimit: o,
            setEnhanceType: l,
            setLimit: c,
            setTimePeriodType: s,
            isLoading: t,
          }
        );
      };
      var th = n(23488);
      let tf = (0, eJ.utcFormat)(".%L"),
        tg = (0, eJ.utcFormat)(":%S"),
        ty = (0, eJ.utcFormat)("%H:%M"),
        tx = (0, eJ.utcFormat)("%H:00"),
        tv = (0, eJ.utcFormat)("%m/%d"),
        tS = (0, eJ.utcFormat)("%m/%d"),
        tb = (0, eJ.utcFormat)("%Y/%m"),
        tT = (0, eJ.utcFormat)("%Y");
      function tj(e, t) {
        if ("4" !== t && "5" !== t) {
          if ((0, eJ.utcSecond)(e) < e) return tf(e);
          if ((0, eJ.utcMinute)(e) < e) return tg(e);
          if ((0, eJ.utcHour)(e) < e) return ty(e);
          if ((0, eJ.utcDay)(e) < e) return tx(e);
        }
        return "5" !== t && (0, eJ.utcMonth)(e) < e
          ? (0, eJ.utcWeek)(e) < e
            ? tv(e)
            : tS(e)
          : (0, eJ.utcYear)(e) < e
            ? tb(e)
            : tT(e);
      }
      var tw = n(22977);
      function tP(e, t) {
        let n = document.getElementById(e);
        if (n && n instanceof Node) {
          for (; n.firstChild; ) n.removeChild(n.firstChild);
          for (let e of t) n.appendChild(e);
        } else
          console.error("ID가 '".concat(e, "'인 요소를 찾을 수 없습니다."));
      }
      let tC = (e, t, n, a, i) => {
          let r = eJ["left" === n ? "axisLeft" : "axisRight"](t)
            .ticks(null != a ? a : 6, "~s")
            .tickSize(8)
            .tickSizeOuter(0)
            .tickPadding(8);
          e.call(
            r.tickFormat((e) => {
              let t = Math.floor(10 * e) / 10;
              return (t.toFixed(1), Number(e) >= 1e3)
                ? Number(e) >= 1e6
                  ? eJ.format(",.1~f")(t / 1e6) + "M"
                  : eJ.format(",.1~f")(t / 1e3) + "K"
                : 0 === e
                  ? "0"
                  : 1 > Number(e)
                    ? eJ.format(".1~f")(t)
                    : eJ.format(",.1~f")(t);
            }),
          )
            .selectAll("text")
            .style("font-size", "".concat(i || 12, "px"));
        },
        tD = 3;
      function tk(e) {
        return new tE("O-" + (null == e ? "" : e + "-") + ++tD);
      }
      class tE {
        toString() {
          return "url(".concat(this.href, ")");
        }
        constructor(e) {
          ((this.id = e),
            (this.href = new URL("#".concat(e), location.href).toString()));
        }
      }
      let tI = (e) => (t) => {
        let n = t.date.getTime();
        return n >= e[0].getTime() && n <= e[1].getTime();
      };
      var tN = n(16206),
        tU = n.n(tN);
      function tR(e) {
        return { 1: 20, 2: 60, 3: 1440, 4: 10080, 5: 43200, 0: 20 }[e];
      }
      function tO(e) {
        return eV().utc(e).format("YYYY-MM-DD HH:mm");
      }
      function tM(e, t, n, a, i) {
        if (!t || 0 === t.length) return null;
        let r = n(e),
          l = 0,
          o = t.length - 1,
          c = 0;
        for (; l <= o; )
          t[(c = Math.floor((l + o) / 2))].date.getTime() < e.getTime()
            ? (l = c + 1)
            : (o = c - 1);
        let s = Math.max(0, c - 5),
          u = Math.min(t.length - 1, c + 5),
          p = null,
          d = 1 / 0;
        for (let e = s; e <= u; e++) {
          let l = t[e];
          if (!l.active || (!l.endPrice && !l.maxPrice)) continue;
          let o = n(l.date);
          if (o <= a || o >= i) continue;
          let c = Math.abs(o - r);
          c < d && ((d = c), (p = l));
        }
        return p;
      }
      eV().extend(tU());
      let tL = (e) => 6e4 * tR(e),
        tz = (e) => !!(e.endPrice || e.maxPrice),
        tB = (e, t, n, a) => {
          let i = a.map((e) => e.date),
            r = -1 / 0,
            l = i.filter((e) => {
              let n = t(e);
              return n - r >= 65 && ((r = n), !0);
            });
          e.call(
            eJ
              .axisBottom(t)
              .tickSize(0)
              .tickPadding(8)
              .tickFormat((e, t) => {
                if (0 === t) return tj(e, n);
                let a = l[t - 1],
                  i = e.getUTCFullYear() !== a.getUTCFullYear(),
                  r = e.getUTCMonth() !== a.getUTCMonth(),
                  o = e.getUTCDate() !== a.getUTCDate();
                if (i) return tT(e);
                if ("4" !== n && "5" !== n) {
                  if (r) return tb(e);
                  if (o) return tv(e);
                }
                return tj(e, n);
              })
              .tickValues(l),
          )
            .selectAll("text")
            .style("font-size", "".concat(11, "px"));
        },
        tF = (e, t, n, a, i) => {
          if (!(null == e ? void 0 : e.length) || e.length < 2) return [0, n];
          let [r, l] = [e[0].date, e[e.length - 1].date];
          return [Math.min(0, t(r) - a / i), t(l) + a / i];
        },
        tG = (e, t, n) => {
          if (t.length <= 1) return 1;
          let a = n(t[0].date);
          return e / 0.8 / (n(t[1].date) - a);
        };
      function tZ(e, t, n, a, i) {
        let {
            tooltipWidth: r = 130,
            width: l = 1020,
            height: o = 484,
            marginTop: c = 0,
            marginRight: s = 52,
            marginBottom: u = 30,
            marginLeft: p = 0,
            barHeight: d = 68,
            isMobile: m = !1,
          } = i,
          h = t.timePeriodType,
          { fontSize: f, fontHeight: g } = m
            ? { fontSize: 12, fontHeight: 14 }
            : { fontSize: 14, fontHeight: 16 },
          y = d + 32,
          x = { right: l - s, width: l - p - s, height: o - u - c },
          v = t.data ? [...t.data] : [];
        v.length >= 0 &&
          v.length < 7 &&
          (v = (function (e) {
            let t =
                arguments.length > 1 && void 0 !== arguments[1]
                  ? arguments[1]
                  : 300,
              n = arguments.length > 2 ? arguments[2] : void 0,
              a = tR(n),
              i = e.length,
              r = t - i,
              l = e.slice();
            if (r > 0 && i > 0) {
              let t = new Date(e[0].date || 0);
              for (let e = 1; e <= r; e++) {
                let i = new Date(t.getTime() - e * a * 6e4);
                "4" === n
                  ? (i = eJ.timeWeek.offset(t, -e))
                  : "5" === n && (i = eJ.timeMonth.offset(t, -e));
                let r = {
                  date: i,
                  avgPrice: 0,
                  minPrice: 0,
                  maxPrice: 0,
                  endPrice: 0,
                  step: 1,
                  totalEnhancementCount: 0,
                  active: !1,
                };
                l.push(r);
              }
            }
            return (
              l.sort((e, t) =>
                e.date && t.date ? e.date.getTime() - t.date.getTime() : 0,
              ),
              l
            );
          })(v, 7, h));
        let S = [...v],
          b = [...v],
          T = b.filter(tz),
          j = (null == T ? void 0 : T.length) ? T[T.length - 1] : void 0,
          w = eJ
            .select(e.current)
            .append("svg")
            .attr("viewBox", [0, 0, l, o])
            .attr("width", l)
            .attr("height", o)
            .attr("id", "dynamic-pricing-graph")
            .attr("style", "max-width: 100%; height: auto;"),
          P = w
            .append("g")
            .attr("transform", "translate(".concat(p, ", ").concat(c, ")")),
          C = tk("clip"),
          D = tk("clip"),
          k = tk("clip");
        (P.append("clipPath")
          .attr("id", C.id)
          .append("rect")
          .attr("x", p + 1)
          .attr("y", -u)
          .attr("width", x.width)
          .attr("height", o),
          P.append("clipPath")
            .attr("id", D.id)
            .append("rect")
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", l)
            .attr("height", x.height + u),
          P.append("clipPath")
            .attr("id", k.id)
            .append("rect")
            .attr("x", p + 1)
            .attr("y", x.height - (y - 32))
            .attr("width", x.width)
            .attr("height", y - 32));
        let E = eJ.extent(v, (e) => e.date),
          I = eJ
            .scaleTime()
            .domain([E[0], E[1]])
            .range([42, x.width - 42]),
          N = eJ
            .scaleLinear()
            .range([x.height - y, c])
            .nice(),
          U = eJ
            .scaleLinear()
            .range([x.height, x.height - (y - 32)])
            .nice(),
          R = P.append("g")
            .attr("clip-path", C.toString())
            .attr("id", "grid-x");
        (R.selectAll("line")
          .attr("stroke", "#D1FAE5")
          .attr("shape-rendering", "crispEdges"),
          R.select("path").attr("stroke", "#868E96"));
        let O = P.append("g")
          .attr("clip-path", C.toString())
          .attr("id", "enhance-grid-x");
        (O.selectAll("line")
          .attr("stroke", "#D1FAE5")
          .attr("shape-rendering", "crispEdges"),
          O.select("path").attr("stroke", "#E9ECEF"));
        let M = P.append("g")
          .attr("transform", "translate(0,".concat(x.height, ")"))
          .attr("clip-path", C.toString())
          .attr("id", "axis-x-bottom");
        (P.append("line")
          .attr("x1", 0)
          .attr("y1", x.height - y)
          .attr("x2", x.width)
          .attr("y2", x.height - y + 1)
          .attr("stroke-width", 1)
          .attr("clip-path", C.toString())
          .attr("id", "axis-x-bottom-minmax"),
          P.append("line")
            .attr("x1", 0)
            .attr("y1", x.height)
            .attr("x2", x.width)
            .attr("y2", x.height + 1)
            .attr("stroke-width", 1)
            .attr("clip-path", C.toString())
            .attr("id", "axis-x-bottom-enhance"));
        let L = P.append("g")
            .attr("clip-path", D.toString())
            .attr("id", "y-axis-price")
            .attr("transform", "translate(".concat(x.width, ", 0)")),
          z = P.append("g")
            .attr("clip-path", D.toString())
            .attr("id", "y-axis-enhance")
            .attr("transform", "translate(".concat(x.width, ", 0)")),
          B = P.append("g")
            .attr("clip-path", k.toString())
            .attr("class", "bars")
            .attr("fill", "#D1FAE5")
            .selectAll("g")
            .data(b),
          F = P.append("g")
            .attr("id", "min-max")
            .attr("clip-path", C.toString())
            .attr("width", x.width)
            .selectAll("g")
            .data(b.filter((e) => e.maxPrice && e.maxPrice !== e.minPrice)),
          G = (e, t) =>
            (0, th.Z)(
              (t) => e(t.date),
              (e) => {
                var n;
                return t(null !== (n = e.endPrice) && void 0 !== n ? n : 0);
              },
            ).defined((e) => void 0 !== e.endPrice && null !== e.endPrice),
          Z = P.append("g")
            .attr("clip-path", C.toString())
            .attr("id", "close-price-line")
            .append("path")
            .attr("transform", "translate(0,0)")
            .attr("fill", "none")
            .attr("stroke", "#69717A")
            .attr("stroke-width", "2px")
            .attr("shape-rendering", "crispEdges"),
          q = P.append("g")
            .attr("id", "rule")
            .attr("clip-path", C.toString())
            .append("line")
            .attr("y1", x.height)
            .attr("y2", -24)
            .attr("stroke", "#21272A")
            .attr("stroke-width", "1px")
            .attr("stroke-dasharray", "3px"),
          H = P.append("g")
            .attr("clip-path", C.toString())
            .append("circle")
            .attr("stroke", "#21272A")
            .attr("stroke-width", "2px")
            .attr("fill", "white")
            .attr("cx", -100)
            .attr("cy", -100)
            .attr("r", 6),
          A = P.append("foreignObject")
            .attr("y", -24)
            .attr("x", -24)
            .attr("width", r)
            .attr("height", 20)
            .attr("class", "tooltip"),
          Y = P.append("g").attr("id", "legend").attr("height", "20px"),
          _ = [
            { color: "#69717A", label: "Close Price", type: "line" },
            { color: "#10B981", label: "NESO Price", type: "rect" },
            { color: "#00B8E5", label: "Enhancement Count", type: "rect" },
          ],
          V = m ? 4 : 16,
          J = (e) => e * (74 + V);
        (Y.attr(
          "transform",
          "translate(".concat(l - (m ? 280 : 320), ", ").concat(o - c - g, ")"),
        ),
          Y.selectAll(".legend-rect")
            .data(_.filter((e) => "rect" === e.type))
            .enter()
            .append("rect")
            .attr("class", "legend-rect")
            .attr("width", 8)
            .attr("height", 8)
            .attr("rx", 2)
            .attr("ry", 2)
            .attr("x", (e) => {
              let { label: t } = e;
              return J(_.findIndex((e) => e.label === t));
            })
            .attr("y", g - 8 - 1)
            .attr("fill", (e) => e.color),
          Y.selectAll(".legend-line")
            .data(_.filter((e) => "line" === e.type))
            .enter()
            .append("line")
            .attr("class", "legend-line")
            .attr("x1", (e) => {
              let { label: t } = e;
              return J(_.findIndex((e) => e.label === t));
            })
            .attr("x2", (e) => {
              let { label: t } = e;
              return J(_.findIndex((e) => e.label === t)) + 8;
            })
            .attr("y1", g - 4 - 1)
            .attr("y2", g - 4 - 1)
            .attr("stroke", (e) => e.color)
            .attr("stroke-width", 2),
          Y.selectAll("text")
            .data(_)
            .enter()
            .append("text")
            .attr("x", (e, t) => J(t) + 8 + 4)
            .attr("y", g)
            .text((e) => e.label)
            .attr("font-size", "".concat(f, "px"))
            .attr("font-family", "inherit")
            .attr("fill", (e) => e.color));
        let W = (e) => {
            let t = null == j ? void 0 : j.date;
            if (!t) {
              (A.html(""),
                q.attr("transform", "translate(0,0)"),
                H.attr("cx", -100).attr("cy", -100));
              return;
            }
            let n = e(t);
            (q.attr(
              "transform",
              "translate(".concat(Math.max(n - 0.5, 1), ",0)"),
            ),
              A.html(t ? "<p>".concat(tO(t), "</p>") : ""));
            let a = x.width - r,
              i = e(t) - r / 2;
            (A.attr("x", a < 0 ? l / 2 - r / 2 : i > a ? a : i < 0 ? 1 : i)
              .select("p")
              .text(tO(t)),
              (null == j ? void 0 : j.endPrice) &&
                H.attr("cx", n).attr("cy", N(j.endPrice)),
              F.attr("stroke", (e) =>
                e.date === t ? "#10B981" : e.date < t ? "#34D399" : "#D1FAE5",
              ),
              B.attr("fill", (e) =>
                e.date === t ? "#0093C4" : e.date < t ? "#11CDF2" : "#C8F6FF",
              ));
          },
          K = async (e) => {
            let t = tL(h),
              [a, i] = e.domain(),
              r = b.filter(tI([new Date(+a - t), new Date(+i + t)])),
              l = null == j ? void 0 : j.date;
            if (!l) {
              let e = null == r ? void 0 : r.filter(tz);
              l = (null == e ? void 0 : e.length) ? e[0].date : void 0;
            }
            return (
              n((j = (l && tM(l, r, e, p, x.right)) || void 0)),
              w.on("mousemove touchmove", (t) => Q(t, r, e)),
              !(function (e) {
                let t = e.filter((e) => !!e.maxPrice),
                  n = e.filter((e) => !!e.endPrice),
                  a = (null == t ? void 0 : t.length)
                    ? (0, eJ.min)(t, (e) => e.minPrice)
                    : void 0,
                  i = (null == n ? void 0 : n.length)
                    ? (0, eJ.min)(n, (e) => e.endPrice)
                    : void 0,
                  r = (0, eJ.max)(e, (e) =>
                    Math.max(e.maxPrice || 0, e.endPrice || 0),
                  ),
                  l = (0, eJ.max)(e, (e) => e.totalEnhancementCount || 0);
                (N.domain([
                  void 0 === a
                    ? i || 0
                    : void 0 === i
                      ? a || 0
                      : Math.min(a, i),
                  r || 100,
                ]).nice(),
                  U.domain([0, null != l ? l : 100]).nice());
              })(r),
              M.call((t) => tB(t, e, h, r)),
              L.transition()
                .ease(eJ.easeLinear)
                .duration(50)
                .call(tC, N, "right ", void 0, 11),
              z
                .transition()
                .ease(eJ.easeLinear)
                .duration(50)
                .call(tC, U, "right ", 3, 11),
              R.call(
                (0, eJ.axisLeft)(N)
                  .ticks(6)
                  .tickSize(-x.width)
                  .tickFormat(function () {
                    return "";
                  }),
              ),
              O.call(
                (0, eJ.axisLeft)(U)
                  .ticks(3)
                  .tickSize(-x.width)
                  .tickFormat(function () {
                    return "";
                  }),
              ),
              !(function (e, t) {
                let n = (function (e, t) {
                    if (e.length <= 1) return 4.8;
                    let n = t(new Date(e[0].date));
                    return Math.max(
                      4.8,
                      Math.min(56, (t(new Date(e[1].date)) - n) * 0.8),
                    );
                  })(e, t),
                  a = (e, t, n, a) => {
                    let i = n(null != e ? e : 0),
                      r = n(null != t ? t : 0),
                      l = a / 2;
                    return Math.abs(i - r) < a
                      ? { y1: i, y2: r }
                      : { y1: i - l, y2: r + l };
                  };
                ((F = F.data(
                  e.filter((e) => e.maxPrice && e.maxPrice !== e.minPrice),
                )
                  .join("line")
                  .attr("stroke-linecap", (e) => {
                    var t, a;
                    return Math.abs(
                      N(null !== (t = e.minPrice) && void 0 !== t ? t : 0) -
                        N(null !== (a = e.maxPrice) && void 0 !== a ? a : 0),
                    ) >= n
                      ? "round"
                      : "butt";
                  })
                  .attr("stroke-width", n)
                  .attr("transform", (e) =>
                    "translate(".concat(t(e.date), ",0)"),
                  )
                  .attr("y1", (e) => {
                    let { y1: t } = a(e.minPrice || 0, e.maxPrice || 0, N, n);
                    return t;
                  })
                  .attr("y2", (e) => {
                    if (null == e.maxPrice) return null;
                    let { y2: t } = a(e.minPrice || 0, e.maxPrice, N, n);
                    return t;
                  })),
                  Z.datum(e.filter((e) => e.endPrice)).attr("d", G(t, N)));
                let i = U(0);
                B = B.data(e)
                  .join("path")
                  .attr("transform", "translate(0,0)")
                  .attr("d", (e) => {
                    if (!e.totalEnhancementCount) return "";
                    let a = U(e.totalEnhancementCount || 0);
                    return (function (e, t, n, a) {
                      let i = Math.min(n / 2, a);
                      return a <= i
                        ? "\n      M "
                            .concat(e, ",")
                            .concat(t + a, "\n      L ")
                            .concat(e, ",")
                            .concat(t, "\n      L ")
                            .concat(e + n, ",")
                            .concat(t, "\n      L ")
                            .concat(e + n, ",")
                            .concat(t + a, "\n      Z\n    ")
                        : "\n    M "
                            .concat(e, ",")
                            .concat(t + a, "\n    L ")
                            .concat(e, ",")
                            .concat(t + i, "\n    A ")
                            .concat(i, ",")
                            .concat(i, " 0 0 1 ")
                            .concat(e + n, ",")
                            .concat(t + i, "\n    L ")
                            .concat(e + n, ",")
                            .concat(t + a, "\n    Z\n  ");
                    })(t(e.date) - n / 2, a, n, i - a);
                  });
              })(r, e),
              W(e),
              !0
            );
          };
        function Q(e, t, a) {
          let i = (0, eJ.pointer)(e)[0],
            r = tM(a.invert(i), t, a, p, x.right);
          (null == r ? void 0 : r.active)
            ? ((j = r), W(a), n({ ...r }))
            : n((j = void 0));
        }
        let X = !1,
          $ = t.minTimestamp;
        w.on("mousemove touchmove", (e) => Q(e, b, I));
        let ee = !1,
          et = async (e) => {
            let n = e.transform,
              i = n.rescaleX(I),
              r = n.invertX(e.transform.x),
              l = i.invert(r - x.width / 3),
              o = new Date(1e3 * $),
              c = 7;
            !(l <= o) || X || ee
              ? (el(n.k), K(i))
              : ((X = !0),
                "1" === h
                  ? (c = 4)
                  : "2" === h
                    ? (c = 7)
                    : "3" === h
                      ? (c = 14)
                      : "4" === h
                        ? (c = 84)
                        : "5" === h && (c = 365),
                (0, tw._)(150).then(() => {
                  var e;
                  let [i, r] = [
                    ((e = -c), eV()(o).add(e, "day")).unix(),
                    eV()(o).unix(),
                  ];
                  (($ = i),
                    a({
                      minTimestamp: i,
                      maxTimestamp: r,
                      timePeriodType: h,
                      itemId: "".concat(t.itemId),
                      itemUpgradeType: "".concat(t.itemUpgradeType),
                      itemUpgradeSubType: "".concat(t.itemUpgradeSubType),
                      itemUpgrade: t.itemUpgrade,
                    })
                      .then((e) => {
                        var t, a;
                        ((e &&
                          (null === (t = e.data) || void 0 === t
                            ? void 0
                            : t.length)) ||
                          (ee = !0),
                          e &&
                            (null === (a = e.data) || void 0 === a
                              ? void 0
                              : a.length) &&
                            ((T = (b = (function (e, t) {
                              let n = new Map();
                              return (
                                e.forEach((e) =>
                                  n.set(e.date.toISOString(), e),
                                ),
                                t.forEach((e) => {
                                  let t = e.date.toISOString(),
                                    a = n.get(t);
                                  (!a ||
                                    Object.keys(a).every(
                                      (e) =>
                                        "date" === e || !a[e] || 0 === a[e],
                                    )) &&
                                    n.set(t, e);
                                }),
                                Array.from(n.values()).sort(
                                  (e, t) => e.date.getTime() - t.date.getTime(),
                                )
                              );
                            })(e.data, b)).filter(tz)),
                            er(),
                            el(n.k)));
                        let i = eJ.zoomTransform(w.node()),
                          r = i.k,
                          l = eJ.extent(b, (e) => e.date),
                          o = i.rescaleX(I),
                          c = I.copy().domain(l),
                          s = c.invert(-i.x / i.k),
                          u = -c(s) * i.k,
                          p = eJ.zoomIdentity.translate(u, i.y).scale(r);
                        (w.call(ei.transform, p),
                          K(o).then((e) => {
                            e && (X = !1);
                          }));
                      })
                      .catch((e) => {
                        (console.error("chart data fetch error", e), (X = !1));
                      }));
                }));
          },
          en = null,
          ea = !1,
          ei = eJ
            .zoom()
            .extent([
              [0, 0],
              [x.right, o],
            ])
            .on("start", function (e) {
              e.sourceEvent &&
                (en = { x: e.transform.x, y: e.transform.y, k: e.transform.k });
            })
            .on("zoom", et)
            .on("end", function (e) {
              if (!e.sourceEvent || !en || X || ea) return;
              let t = { x: e.transform.x, y: e.transform.y },
                n = e.transform,
                a = t.x - en.x,
                i = t.y - en.y,
                r = n.k,
                l = n.x;
              if (r !== en.k || 0 === a || Math.abs(a) < Math.abs(i)) return;
              ea = !0;
              let o = l + 1.8 * a,
                [c, s] = tF(T, I, x.right, 42, r),
                u = -c * r,
                p = x.width - s * r;
              o > u ? (o = u) : o < p && (o = p);
              let d = eJ.zoomIdentity.translate(o, 0).scale(r);
              (w
                .transition()
                .duration(400)
                .ease(eJ.easeCircleOut)
                .call(ei.transform, d)
                .on("end", () => {
                  ea = !1;
                }),
                (en = null));
            }),
          er = () => {
            let e = (function (e) {
              let { initialData: t, data: n, xScale: a } = e;
              if (n.length <= 1) return [1, 1];
              let [i, r] = a.range(),
                l = r - i,
                o = l / t.length;
              return [Math.max(l / n.length / o, tG(4.8, n, a)), tG(56, n, a)];
            })({ initialData: S, data: b, period: h, xScale: I });
            return (ei.scaleExtent([e[0], e[1]]), e);
          },
          el = (e) => {
            let t = tF(T, I, x.right, 42, e);
            ei.translateExtent([
              [t[0], 0],
              [t[1], o],
            ]);
          },
          eo = er(),
          ec = eo[0];
        el(eo[0]);
        let es = 0,
          eu = b.filter(tz);
        if (null == eu ? void 0 : eu.length) {
          var ep;
          let e = I(
            new Date(
              null === (ep = eu[eu.length - 1]) || void 0 === ep
                ? void 0
                : ep.date,
            ),
          );
          es = x.width - e * ec - 42;
        }
        return (
          w
            .call(ei)
            .call(ei.transform, eJ.zoomIdentity.translate(es, 0).scale(ec)),
          w.node()
        );
      }
      let tq = (e, t) => ({
          date: new Date(null == e ? void 0 : e.date),
          avgPrice: (null == e ? void 0 : e.avgPrice) || 0,
          minPrice: (null == e ? void 0 : e.minPrice) || 0,
          maxPrice: (null == e ? void 0 : e.maxPrice) || 0,
          endPrice: (null == e ? void 0 : e.endPrice) || 0,
          step: (null == e ? void 0 : e.step) === 2 ? 2 : 1,
          totalEnhancementCount: (null == e ? void 0 : e.sumEnhanceCnt) || 0,
          active: t || !1,
        }),
        tH = function (e) {
          let t =
            !(arguments.length > 1) || void 0 === arguments[1] || arguments[1];
          return (
            (null == e
              ? void 0
              : e
                  .filter((e) => !!(null == e ? void 0 : e.date))
                  .map((e) => tq(e, t))) || []
          );
        };
      async function tA(e) {
        return await new w.Z()
          .getHistory({
            itemId: e.itemId,
            itemUpgradeType: e.itemUpgradeType || void 0,
            itemUpgrade:
              e.itemUpgrade || ("0" === e.itemUpgradeType ? 0 : void 0),
            itemUpgradeSubType:
              "1" === e.itemUpgradeType
                ? ""
                    .concat(
                      e.itemUpgradeSubType && "0" !== e.itemUpgradeSubType
                        ? e.itemUpgradeSubType
                        : e2[0].value,
                    )
                    .toString()
                : void 0,
            timePeriodType: e.timePeriodType,
            minTimestamp: e.minTimestamp,
            maxTimestamp: (function (e) {
              let t = new Date(1e3 * e),
                n = 10 * Math.floor(t.getMinutes() / 10);
              return (t.setMinutes(n, 0, 0), Math.floor(t.getTime() / 1e3));
            })(e.maxTimestamp),
          })
          .then((t) => {
            if (t) return { ...e, data: tH(t.points, !0) };
          });
      }
      Promise.all([n.e(7336), n.e(4822)]).then(n.t.bind(n, 54822, 23));
      let tY = {
          maxPrice: void 0,
          minPrice: void 0,
          endPrice: void 0,
          totalEnhancementCount: void 0,
          date: void 0,
        },
        t_ = (0, P.forwardRef)((e, t) => {
          let { itemId: n } = e,
            {
              currentLimit: a,
              enhanceType: r,
              setTimePeriodType: l,
              isLoading: o,
            } = tm(n);
          (0, P.useRef)(r).current = r;
          let {
              itemUpgrade: c,
              itemUpgradeSubType: s,
              itemUpgradeType: u,
              minTimestamp: p,
              maxTimestamp: d,
              timePeriodType: m,
            } = eQ(),
            [h, f] = (0, P.useState)(!0),
            [g, y] = (0, P.useState)(tY),
            x = (0, P.useRef)(null),
            v = (0, P.useRef)(null),
            { width: S } = eX(v),
            b = (0, P.useRef)(S);
          b.current = S;
          let T = (0, P.useRef)(void 0),
            j = (0, P.useRef)(!1),
            w = (0, P.useCallback)((e) => {
              y(e || tY);
            }, []),
            C = (0, P.useCallback)(async () => {
              var e, t;
              let a = (null == r ? void 0 : r.includes("starforce")) ? u : "1",
                i = (null == r ? void 0 : r.includes("potential"))
                  ? s || "2711000"
                  : void 0,
                l = {
                  itemId: n,
                  timePeriodType: m || "1",
                  minTimestamp: p,
                  maxTimestamp: d,
                  itemUpgrade: c || ("0" === a ? 0 : void 0),
                  itemUpgradeType: a || void 0,
                  itemUpgradeSubType: i,
                },
                o = await tA(l).catch((e) => {
                  console.error(e);
                });
              return {
                itemId: n,
                itemUpgrade: l.itemUpgrade || 0,
                itemUpgradeType:
                  null !== (e = l.itemUpgradeType) && void 0 !== e ? e : "0",
                itemUpgradeSubType: null != i ? i : e2[0].value,
                timePeriodType: l.timePeriodType,
                data:
                  o &&
                  null !== (t = null == o ? void 0 : o.data) &&
                  void 0 !== t
                    ? t
                    : [],
                minTimestamp: p,
                maxTimestamp: d,
              };
            }, [n, c, s, u, d, p, m, r]),
            D = (0, P.useCallback)(() => {
              ((j.current = !1),
                f(!1),
                w(void 0),
                x.current &&
                  "innerHTML" in x.current &&
                  (x.current.innerHTML = ""));
            }, [w]),
            k = (0, P.useCallback)(() => {
              j.current ||
                o ||
                ((j.current = !0),
                C().then((e) => {
                  var t;
                  if (
                    ((j.current = !1),
                    (T.current = e),
                    (null == e
                      ? void 0
                      : null === (t = e.data) || void 0 === t
                        ? void 0
                        : t.length) > 0)
                  ) {
                    f(!0);
                    let t = b.current < +eS.xz;
                    tP(e$, [
                      tZ(x, e, w, tA, {
                        tooltipWidth: 130,
                        width: b.current,
                        height: 484,
                        marginTop: 24,
                        marginRight: 52,
                        marginBottom: 50,
                        marginLeft: 0,
                        barHeight: 90,
                        graphRightPaddingSize: 0.5,
                        isMobile: t,
                      }),
                    ]);
                  } else D();
                }));
            }, [C, w, D, j, o]);
          return (
            (0, P.useImperativeHandle)(t, () => ({ refresh: k }), [k]),
            (0, P.useEffect)(() => {
              var e, t;
              T.current &&
                (null === (t = T.current) || void 0 === t
                  ? void 0
                  : null === (e = t.data) || void 0 === e
                    ? void 0
                    : e.length) &&
                tP(e$, [
                  tZ(x, T.current, w, tA, {
                    tooltipWidth: 130,
                    width: S,
                    height: 484,
                    marginTop: 24,
                    marginRight: 52,
                    marginBottom: 50,
                    marginLeft: 0,
                    barHeight: 90,
                    graphRightPaddingSize: 0.5,
                  }),
                ]);
            }, [w, S]),
            (0, P.useEffect)(() => {
              n ? k() : D();
            }, [D, k, C, n]),
            (0, i.jsxs)("article", {
              className: e1().container,
              children: [
                (0, i.jsx)(td, {
                  maxPrice: g.maxPrice,
                  minPrice: g.minPrice,
                  endPrice: g.endPrice,
                  totalEnhancementCount: g.totalEnhancementCount,
                  currentLimit: a,
                  enhanceType: r,
                  timePeriodType: m,
                  setTimePeriodType: l,
                }),
                (0, i.jsxs)("div", {
                  className: e1().graphContainer,
                  ref: v,
                  children: [
                    (0, i.jsx)("section", {
                      ref: x,
                      id: e$,
                      className: e1().graph,
                    }),
                    !h && (0, i.jsx)(O, {}),
                  ],
                }),
              ],
            })
          );
        });
      var tV = function (e) {
        let { itemId: t } = e.params,
          { enhanceType: n } = tm(t);
        if (!t) {
          console.error("id not found.");
          return;
        }
        return (0, i.jsxs)("main", {
          className: l().page,
          children: [
            (0, i.jsx)(ev, { itemId: t }),
            (0, i.jsxs)("article", {
              className: l().pageInformationData,
              children: [
                (0, i.jsx)("div", {
                  className: l().pageInformationHeader,
                  children: (0, i.jsx)(o.Z, {
                    type: "heading-xxl-bold",
                    as: "span",
                    children: "Dynamic Pricing Information",
                  }),
                }),
                (0, i.jsx)(d, {
                  title: "",
                  className: l().pageInformationDataGap,
                  children: (0, i.jsx)("div", {
                    style: { width: "100%", overflowX: "auto" },
                    children: (0, i.jsx)(t_, { itemId: t }),
                  }),
                }),
                n.includes("starforce") &&
                  (0, i.jsxs)(i.Fragment, {
                    children: [
                      (0, i.jsx)("div", {
                        className: l().pageInformationHeader,
                        children: (0, i.jsx)(o.Z, {
                          type: "heading-xxl-bold",
                          as: "span",
                          children: "Starforce Enhancement Prices",
                        }),
                      }),
                      (0, i.jsx)(G, { itemId: t }),
                    ],
                  }),
                n.includes("potential") &&
                  (0, i.jsxs)(i.Fragment, {
                    children: [
                      (0, i.jsx)("div", {
                        className: l().pageInformationHeader,
                        children: (0, i.jsx)(o.Z, {
                          type: "heading-xxl-bold",
                          as: "span",
                          children: "Potential Enhancement Prices",
                        }),
                      }),
                      (0, i.jsx)(J, { itemId: t }),
                    ],
                  }),
              ],
            }),
          ],
        });
      };
    },
    42254: function (e, t, n) {
      "use strict";
      var a = n(57437),
        i = n(2265),
        r = n(44889),
        l = n.n(r),
        o = n(23619),
        c = n(36760),
        s = n.n(c),
        u = n(79415),
        p = n(84971);
      t.Z = function (e) {
        let { className: t } = e,
          [{ searchValue: n }, r] = (0, o.j)(),
          [c, d] = (0, i.useState)(n || ""),
          m = (0, i.useCallback)(
            (e) => {
              if (0 === e.length) {
                (0, u.eS)({
                  message: "Please enter a search term.",
                  duration: 3500,
                  type: "success",
                });
                return;
              }
              r({ searchValue: e });
            },
            [r],
          ),
          h = (0, i.useCallback)((e) => {
            d(e);
          }, []),
          f = (0, i.useCallback)(() => {
            (d(""), r({ searchValue: "" }));
          }, [r]),
          g = (0, i.useCallback)(
            (e) => {
              (e.preventDefault(), m(c));
            },
            [c, m],
          );
        return (0, a.jsx)("form", {
          onSubmit: g,
          children: (0, a.jsx)(p.e, {
            className: s()(t, l().search),
            placeholder: "Search",
            onChange: (e) => h(e.target.value),
            onClear: f,
            value: c,
          }),
        });
      };
    },
    62692: function (e, t, n) {
      "use strict";
      n.d(t, {
        u: function () {
          return a;
        },
      });
      let a = [
        { value: "WEAPON", label: "Weapons" },
        { value: "SUB_WEAPON", label: "S. Weapon" },
        { value: "CAP", label: "Hat" },
        { value: "CLOTHES", label: "Outfit" },
        { value: "SHOES", label: "Shoes" },
        { value: "GLOVES", label: "Gloves" },
        { value: "CAPE", label: "Cape" },
        { value: "FOREHEAD", label: "Face Accessory" },
        { value: "EYE_ACC", label: "Eye Accessory" },
        { value: "EAR_ACC", label: "Earrings" },
        { value: "RING", label: "Ring" },
        { value: "PENDANT", label: "Pendant" },
        { value: "BELT", label: "Belt" },
        { value: "SHOULDER", label: "Shoulder Accessory" },
        { value: "EMBLEM", label: "Emblem" },
      ];
    },
    87906: function (e, t, n) {
      "use strict";
      var a;
      n.d(t, {
        Bd: function () {
          return S;
        },
        KY: function () {
          return d;
        },
        Lr: function () {
          return p;
        },
        Mg: function () {
          return i;
        },
        Uh: function () {
          return s;
        },
        fk: function () {
          return r;
        },
        fz: function () {
          return y;
        },
        gM: function () {
          return b;
        },
        jO: function () {
          return v;
        },
        kt: function () {
          return x;
        },
        md: function () {
          return u;
        },
        n7: function () {
          return c;
        },
        st: function () {
          return l;
        },
        tH: function () {
          return o;
        },
      });
      let i = "/gamestatus",
        r = "ranking",
        l = "dynamicpricing",
        o = "probabilityitems",
        c = "/guide",
        s = "classes-and-jobs",
        u = "beginnersguide",
        p = "downloadguide",
        d = "/news",
        m = "notices",
        h = "update",
        f = "events",
        g = "style-raffles",
        y = { [m]: m, [h]: h, [f]: f, [g]: g },
        x = [
          { label: "Ranking", value: r, href: "".concat(i, "/").concat(r) },
          {
            label: "Dynamic Pricing",
            value: l,
            href: "".concat(i, "/").concat(l),
          },
          {
            label: "Probability Info",
            value: o,
            href: "".concat(i, "/").concat(o),
          },
        ],
        v =
          null === (a = x.find((e) => e.value === l)) || void 0 === a
            ? void 0
            : a.href,
        S = [
          {
            label: "Classes & Jobs",
            value: "".concat(c, "/").concat(s),
            href: "".concat(c, "/").concat(s),
          },
          {
            label: "Beginner’s Guide",
            value: "".concat(c, "/").concat(u),
            href: "https://docs.maplestoryn.io/msn-101/beginners-guide",
            target: "_blank",
            type: "outLink",
          },
          {
            label: "Download Guide",
            value: "".concat(c, "/").concat(p),
            href: "".concat(c, "/").concat(p),
          },
        ],
        b = [
          {
            label: "Notices",
            value: "".concat(d, "/").concat(m),
            href: "".concat(d, "/").concat(m),
          },
          {
            label: "Update",
            value: "".concat(d, "/").concat(h),
            href: "".concat(d, "/").concat(h),
          },
          {
            label: "Events",
            value: "".concat(d, "/").concat(f),
            href: "".concat(d, "/").concat(f),
          },
          {
            label: "Style Raffles",
            value: "".concat(d, "/").concat(g),
            href: "".concat(d, "/").concat(g),
          },
        ];
    },
    24540: function (e, t, n) {
      "use strict";
      function a(e) {
        return e ? e.charAt(0).toUpperCase() + e.slice(1).toLowerCase() : "";
      }
      n.d(t, {
        f: function () {
          return a;
        },
      });
    },
    97747: function (e, t, n) {
      "use strict";
      n.d(t, {
        P: function () {
          return r;
        },
      });
      var a = n(24540),
        i = n(62692);
      function r(e) {
        let t,
          n = e.equipLevelType;
        if (
          (n.startsWith("RANGE_") && (n = n.substring(6)),
          (n = n.replace("_TO_", "~")),
          (n = "Equip LV ".concat(n)),
          "NORMAL_GROWTH" === e.equipType.toUpperCase())
        )
          t = "Normal - Unchained Set";
        else {
          let n = (t = e.equipType.toLowerCase()).split("_");
          t =
            n.length > 1
              ? ""
                  .concat((0, a.f)(n[0]), " - ")
                  .concat(n.slice(1).map(a.f).join(" "))
              : (0, a.f)(t);
        }
        let r = i.u.find((t) => t.value === e.equipPartType),
          l = r ? r.label : e.equipPartType;
        return "".concat(n, " / ").concat(t, " / ").concat(l);
      }
    },
    38433: function (e, t, n) {
      "use strict";
      function a(e) {
        let t =
            arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : 0,
          n = "string" == typeof e ? parseFloat(e) : e;
        return isNaN(n)
          ? "Invalid input: Please provide a valid number or numeric string."
          : new Intl.NumberFormat("en-US", {
              minimumFractionDigits: t,
              maximumFractionDigits: 20,
            }).format(n);
      }
      n.d(t, {
        p: function () {
          return a;
        },
      });
    },
    48321: function (e, t, n) {
      "use strict";
      n.d(t, {
        r: function () {
          return i;
        },
      });
      var a = n(15353);
      let i = (e) =>
        "boolean" != typeof e &&
        (null == e ||
          "" === e ||
          ("string" == typeof e || Array.isArray(e)
            ? 0 === e.length
            : "object" == typeof e && 0 === Object.keys(e).length))
          ? "/images/unknown_ft.png"
          : "".concat(a.Fv, "/itemimages/icon/").concat(e, ".png");
    },
    54419: function (e, t, n) {
      "use strict";
      n.d(t, {
        z: function () {
          return r;
        },
      });
      var a = n(49211),
        i = n.n(a);
      async function r(e) {
        return new Promise((t) => {
          (i()(e), t(!0));
        });
      }
    },
    82633: function (e, t, n) {
      "use strict";
      n.d(t, {
        R: function () {
          return r;
        },
        P: function () {
          return i;
        },
      });
      let a = (e, t) => {
          let n = encodeURIComponent(null != t ? t : window.location.href);
          window.open("".concat(e).concat(n), "_blank");
        },
        i = (e) => {
          a("https://twitter.com/intent/tweet?text=&url=", e);
        },
        r = (e) => {
          a("https://www.facebook.com/sharer/sharer.php?u=", e);
        };
    },
    23619: function (e, t, n) {
      "use strict";
      n.d(t, {
        j: function () {
          return r;
        },
      });
      var a = n(52994);
      let i = { searchValue: a.Oi.withDefault("") };
      function r() {
        return (0, a.XI)(i, { history: "replace", scroll: !1 });
      }
    },
    71620: function (e) {
      e.exports = {
        page: "Page_page__oyCzJ",
        "page--header": "Page_page--header__mkoGz",
        pageHeader: "Page_page--header__mkoGz",
        "page--description-margin": "Page_page--description-margin__CcdWz",
        pageDescriptionMargin: "Page_page--description-margin__CcdWz",
        "page--information-header": "Page_page--information-header__Oqafl",
        pageInformationHeader: "Page_page--information-header__Oqafl",
        "page--information-data": "Page_page--information-data__9Uzpz",
        pageInformationData: "Page_page--information-data__9Uzpz",
        "page--information-data--gap":
          "Page_page--information-data--gap__pvrvi",
        pageInformationDataGap: "Page_page--information-data--gap__pvrvi",
      };
    },
    12581: function (e) {
      e.exports = {
        section: "EmptyLatestEnhancementSection_section__j8btv",
        section__highlight:
          "EmptyLatestEnhancementSection_section__highlight__cAFj8",
        sectionHighlight:
          "EmptyLatestEnhancementSection_section__highlight__cAFj8",
      };
    },
    53415: function (e) {
      e.exports = {
        potentialTableContainer:
          "_EnhancementCostSection_potentialTableContainer__HY4L3",
        "potentialTableContainer--table":
          "_EnhancementCostSection_potentialTableContainer--table__Raoyf",
        potentialTableContainerTable:
          "_EnhancementCostSection_potentialTableContainer--table__Raoyf",
        tableContainer: "_EnhancementCostSection_tableContainer__xnZB_",
        "tableContainer--table":
          "_EnhancementCostSection_tableContainer--table__4_vsb",
        tableContainerTable:
          "_EnhancementCostSection_tableContainer--table__4_vsb",
        "tableContainer--table--box":
          "_EnhancementCostSection_tableContainer--table--box__dDuzy",
        tableContainerTableBox:
          "_EnhancementCostSection_tableContainer--table--box__dDuzy",
        price: "_EnhancementCostSection_price__B_hyt",
      };
    },
    99451: function (e) {
      e.exports = {
        guideText: "_GuideText_guideText__zhEA7",
        guideDesc: "_GuideText_guideDesc__XenA8",
        guideDate: "_GuideText_guideDate__WB7o_",
        lastUpdatedMargin: "_GuideText_lastUpdatedMargin__1WZSx",
      };
    },
    58272: function (e) {
      e.exports = {
        header: "_Header_header__EbYYS",
        dynamicPricingSearchStyle: "_Header_dynamicPricingSearchStyle__GQa36",
      };
    },
    3093: function (e) {
      e.exports = {
        informationSection: "_InformationSection_informationSection___LLbw",
        "informationSection--contents":
          "_InformationSection_informationSection--contents__sswCj",
        informationSectionContents:
          "_InformationSection_informationSection--contents__sswCj",
      };
    },
    68763: function (e) {
      e.exports = {
        itemDescription: "_ItemDetailComponent_itemDescription__6yIgA",
        itemDescriptionContainer:
          "_ItemDetailComponent_itemDescriptionContainer__50CZt",
        itemDescriptionImageContainer:
          "_ItemDetailComponent_itemDescriptionImageContainer__oW4xF",
        itemDescriptionBox: "_ItemDetailComponent_itemDescriptionBox__F5SDK",
        "itemDescription--buttonContainer":
          "_ItemDetailComponent_itemDescription--buttonContainer__7J4t6",
        itemDescriptionButtonContainer:
          "_ItemDetailComponent_itemDescription--buttonContainer__7J4t6",
        "itemDescription--buttonContainer--box":
          "_ItemDetailComponent_itemDescription--buttonContainer--box__aNUA4",
        itemDescriptionButtonContainerBox:
          "_ItemDetailComponent_itemDescription--buttonContainer--box__aNUA4",
        "itemDescription--buttonContainer--box--Button":
          "_ItemDetailComponent_itemDescription--buttonContainer--box--Button__BOFr3",
        itemDescriptionButtonContainerBoxButton:
          "_ItemDetailComponent_itemDescription--buttonContainer--box--Button__BOFr3",
        "itemDescription--buttonContainer--box--circeBtn":
          "_ItemDetailComponent_itemDescription--buttonContainer--box--circeBtn__qxaNP",
        itemDescriptionButtonContainerBoxCirceBtn:
          "_ItemDetailComponent_itemDescription--buttonContainer--box--circeBtn__qxaNP",
        shareButtonWrapper: "_ItemDetailComponent_shareButtonWrapper__P76wt",
        snsLinkBox: "_ItemDetailComponent_snsLinkBox__bKdOj",
      };
    },
    4455: function (e) {
      e.exports = {
        decimalPriceComponentStyle:
          "DecimalPrice_decimalPriceComponentStyle__vdvXe",
        powerIconStyle: "DecimalPrice_powerIconStyle__rMzsm",
        decimalDotStyle: "DecimalPrice_decimalDotStyle__9tNEP",
        zeroPaddingStyle: "DecimalPrice_zeroPaddingStyle__rRMHh",
      };
    },
    14229: function (e) {
      e.exports = {
        container: "DynamicPricingChart_container__2SbLr",
        graphContainer: "DynamicPricingChart_graphContainer__byvPc",
        graph: "DynamicPricingChart_graph__MfODx",
        periodList: "DynamicPricingChart_periodList__TvXxT",
      };
    },
    833: function (e) {
      e.exports = {
        optionsContainerStyle: "OptionSelector_optionsContainerStyle__TIgfr",
        mobileOptionSelectBtnContainerStyle:
          "OptionSelector_mobileOptionSelectBtnContainerStyle__2OJSu",
        upgradeTypeDropdownStyle:
          "OptionSelector_upgradeTypeDropdownStyle__WX3F1",
        mobileOptionSelectButtonStyle:
          "OptionSelector_mobileOptionSelectButtonStyle__W_7Y2",
        gridRepeat3Style: "OptionSelector_gridRepeat3Style__DmrDX",
        gridRepeat2Style: "OptionSelector_gridRepeat2Style__oa9JB",
        optionButtonStyle: "OptionSelector_optionButtonStyle__BOsfO",
        optionSelectWrap: "OptionSelector_optionSelectWrap__vQ6mM",
        optionButtonActive: "OptionSelector_optionButtonActive__JSggQ",
        enhancementInfoStyle: "OptionSelector_enhancementInfoStyle__6ptKK",
        activeBlueColor: "OptionSelector_activeBlueColor__4ikrR",
        optionLabel: "OptionSelector_optionLabel___76Gc",
      };
    },
    3357: function (e) {
      e.exports = {
        selectChip: "selectChip_selectChip__b40F5",
        square: "selectChip_square__rRKWp",
        pill: "selectChip_pill__H1a3N",
        filled: "selectChip_filled__CPmih",
        outlined: "selectChip_outlined__kL404",
        ghost: "selectChip_ghost__G9YaT",
      };
    },
    73719: function (e) {
      e.exports = {
        mobileOptionSelectBtnContainerStyle:
          "PriceDescription_mobileOptionSelectBtnContainerStyle__HMcrW",
        arrowSpacingStyle: "PriceDescription_arrowSpacingStyle__Ws93O",
        timePeriodButtonContainerStyle:
          "PriceDescription_timePeriodButtonContainerStyle__ajkai",
        chipWrap: "PriceDescription_chipWrap__EjSKX",
        selectBoxStyle: "PriceDescription_selectBoxStyle__EjjTz",
        mobileOptionSelectButtonStyle:
          "PriceDescription_mobileOptionSelectButtonStyle__tPKMh",
        priceDescriptionContainerStyle:
          "PriceDescription_priceDescriptionContainerStyle__WH4Su",
        closePriceDescriptionDatalistStyle:
          "PriceDescription_closePriceDescriptionDatalistStyle__j_nuf",
        rangePriceDescriptionDatalistBoxStyle:
          "PriceDescription_rangePriceDescriptionDatalistBoxStyle__3onCF",
        rangePriceDescriptionDatalistStyle:
          "PriceDescription_rangePriceDescriptionDatalistStyle__t322r",
        enhanceDescriptionDatalistStyle:
          "PriceDescription_enhanceDescriptionDatalistStyle__cDqsK",
        priceDescriptionPriceTextStyle:
          "PriceDescription_priceDescriptionPriceTextStyle__U98_d",
        priceDescriptionPriceValueStyle:
          "PriceDescription_priceDescriptionPriceValueStyle__Co3mt",
        priceDividerStyle: "PriceDescription_priceDividerStyle__jlTIo",
      };
    },
    59914: function (e) {
      e.exports = {
        container: "EmptyData_container__e7pyU",
        link: "EmptyData_link__ygwlA",
      };
    },
    86453: function (e) {
      e.exports = { formingPrice: "FormingPrice_formingPrice__y3L7e" };
    },
    31365: function (e) {
      e.exports = {
        "item-image": "TableItemImage_item-image__NCWtF",
        itemImage: "TableItemImage_item-image__NCWtF",
      };
    },
    44889: function (e) {
      e.exports = { search: "QuerySearch_search__KQ0_z" };
    },
  },
  function (e) {
    (e.O(
      0,
      [
        7243, 6140, 9901, 2482, 2722, 5865, 7069, 3758, 4658, 3884, 6155, 3188,
        1845, 5432, 6028, 5235, 3478, 6408, 5953, 9259, 2606, 7854, 1647, 7648,
        7297, 539, 1434, 8936, 6242, 8710, 2086, 9433, 6165, 9527, 2971, 2117,
        1744,
      ],
      function () {
        return e((e.s = 34496));
      },
    ),
      (_N_E = e.O()));
  },
]);
//# sourceMappingURL=page-844f077f575076a1.js.map
