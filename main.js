const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");
const apiUrl = "http://127.0.0.1:8000/uploadfile/";
const pdfFilePath = "hey.pdf";

const formData = new FormData();
formData.append("file", fs.createReadStream(pdfFilePath));

axios
  .post(apiUrl, formData, {
    headers: {
      "Content-Type": formData.getHeaders()["Content-Type"],
    },
  })
  .then((response) => {
    console.log("Response:", response.data);
  })
  .catch((error) => {
    console.error("Error:", error);
  });
