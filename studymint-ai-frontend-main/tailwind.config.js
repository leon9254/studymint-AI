export default {
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    theme: {
        extend: {
            colors: {
                ink: {
                    50: "#f7f9f6",
                    100: "#ecf0ed",
                    200: "#d7ded9",
                    300: "#b7c3bc",
                    400: "#87978f",
                    500: "#627167",
                    600: "#48564d",
                    700: "#344039",
                    800: "#232d27",
                    900: "#151d18",
                    950: "#0b100d"
                },
                mint: {
                    50: "#eefcf6",
                    100: "#d8f7e9",
                    200: "#aceed1",
                    300: "#72ddb1",
                    400: "#37c48d",
                    500: "#149e70",
                    600: "#0d7f5c",
                    700: "#0b664b",
                    800: "#0a513d",
                    900: "#094333",
                    950: "#04251d"
                },
                saffron: {
                    50: "#fff8e8",
                    100: "#ffefc2",
                    200: "#ffdb7a",
                    300: "#ffc746",
                    400: "#f6ad18",
                    500: "#d98d06",
                    600: "#b86d04",
                    700: "#934f08",
                    800: "#783f0d",
                    900: "#663610",
                    950: "#3a1a03"
                },
                iris: {
                    50: "#f3f5ff",
                    100: "#e7ebff",
                    200: "#ccd5ff",
                    300: "#a7b6ff",
                    400: "#7c8cf6",
                    500: "#5a63dd",
                    600: "#4647bd",
                    700: "#3b3b99",
                    800: "#343576",
                    900: "#30335f",
                    950: "#1d1e37"
                }
            },
            boxShadow: {
                panel: "0 20px 55px rgba(21, 29, 24, 0.10)",
                soft: "0 12px 30px rgba(21, 29, 24, 0.08)"
            },
            fontFamily: {
                sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
            }
        }
    },
    plugins: []
};
