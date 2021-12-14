import os, re
from jsonpath_ng import parse
import openapiart.goserver.string_util as util
import openapiart.goserver.generator_context as ctx
from openapiart.goserver.writer import Writer

class GoServerControllerGenerator(object):

    def __init__(self, ctx):
        # type: (ctx.GeneratorContext) -> None
        self._indent = '\t'
        self._root_package = ctx.module_path
        self._package_name = "controllers"
        self._ctx = ctx
        self._output_path = os.path.join(ctx.output_path, 'controllers')
    
    def generate(self):
        self._write_controllers()

    def _write_controllers(self):
        if not os.path.exists(self._output_path):
            os.makedirs(self._output_path)
        for ctrl in self._ctx.controllers:
            self._write_controller(ctrl)

    def _write_controller(self, ctrl):
        # type: (ctx.Controller) -> None
        filename = ctrl.yamlname.lower() + "_controller.go"
        fullname = os.path.join(self._output_path, filename)
        w = Writer(self._indent)
        self._write_header(w)
        self._write_import(w)
        self._write_controller_struct(w, ctrl)
        self._write_newcontroller(w, ctrl)
        self._write_routes(w, ctrl)
        self._write_methods(w, ctrl)
        with open(fullname, 'w') as file:
            print("Controller: {}".format(fullname))
            for line in w.strings:
                file.write(line + '\n')

    def _write_header(self, w):
        # type: (Writer) -> None
        w.write_line(
            """// This file is autogenerated. Do not modify
            package {package_name}
            """.format(package_name=self._package_name)
        )

    def _write_import(self, w):
        # type: (Writer) -> None
        w.write_line(
            "import ("
        ).push_indent(
        ).write_line(
            """\"io/ioutil"
            "net/http"
            "google.golang.org/protobuf/encoding/protojson"
            "{root_package}/httpapi"
            "{root_package}/httpapi/interfaces"
            {models_prefix} "{models_path}\"""".format(
                root_package=self._root_package,
                models_prefix=re.sub("[.]", "", self._ctx.models_prefix),
                models_path=self._ctx.models_path
            )
        ).pop_indent(
        ).write_line(
            ")",
            ""
        )

    def _struct_name(self, ctrl):
        # type: (ctx.Controller) -> str
        return util.camel_case(ctrl.controller_name)
    
    def _write_controller_struct(self, w, ctrl):
        # type: (Writer, ctx.Controller) -> None
        w.write_line(
            "type {name} struct {{".format(
                name=self._struct_name(ctrl)
            )
        )
        w.push_indent()
        w.write_line(
            "handler interfaces.{name}".format(
                name=ctrl.service_handler_name
            )
        )
        w.pop_indent()
        w.write_line(
            "}",
            ""
        )

    def _write_newcontroller(self, w, ctrl):
        # type: (Writer, ctx.Controller) -> None
        w.write_line(
            "func NewHttp{ctl_name}(handler interfaces.{handle_name}) interfaces.{ctl_name} {{".format(
                ctl_name=ctrl.controller_name,
                handle_name=ctrl.service_handler_name
            )
        ).push_indent()
        w.write_line(
            "return &{name}{{handler}}".format(
                name=self._struct_name(ctrl)
            )
        ).pop_indent()
        w.write_line(
            "}",
            ""
        )

    def _write_routes(self, w, ctrl):
        # type: (Writer, ctx.Controller) -> None
        w.write_line(
            "func (ctrl *{name}) Routes() []httpapi.Route {{".format(
                name=self._struct_name(ctrl)
            )
        ).push_indent()
        w.write_line(
            "return [] httpapi.Route {"
        ).push_indent()
        for r in ctrl.routes:
            w.write_line(
                """{{ Path: "{url}", Method: "{method}", Name: "{operation_name}", Handler: ctrl.{operation_name}}},""".format(
                    url=r.url,
                    method=r.method,
                    operation_name=r.operation_name
                )
            )
        w.pop_indent()
        w.write_line(
            "}",
        ).pop_indent()
        w.write_line(
            "}",
            ""
        )

    def _write_methods(self, w, ctrl):
        # type: (Writer, ctx.Controller) -> None
        self._has_warning_check = False
        for route in ctrl.routes:
            self._write_method(w, ctrl, route)
        if self._has_warning_check:
            w.write_line("""var {name}MrlOpts = protojson.MarshalOptions{{
                    UseProtoNames:   true,
                    AllowPartial:    true,
                    EmitUnpopulated: true,
                    Indent:          "  ",
                }}""".format(
                name=util.camel_case(ctrl.yamlname)
            ))

    def _write_method(self, w, ctrl, route):
        # type: (Writer, ctx.Controller,ctx.ControllerRoute) -> None
        w.write_line("/*")
        w.write_line("{operation_name}: {method} {url}".format(
            operation_name=route.operation_name,
            method=route.method,
            url=route.url
        ))
        w.write_line("Description: " + route.description)
        w.write_line("*/")
        w.write_line(
            "func (ctrl *{name}) {opt_name}(w http.ResponseWriter, r *http.Request) {{".format(
                name=self._struct_name(ctrl),
                opt_name=route.operation_name
            )
        )
        w.push_indent()
        request_body = route.requestBody()   # type: ctx.Component
        rsp_400_error = "response{}400".format(route.operation_name)
        rsp_500_error = "response{}500".format(route.operation_name)
        rsp_errors = [500]
        if request_body != None:
            rsp_errors.append(400)
            modelname = request_body.model_name
            full_modelname = request_body.full_model_name
            new_modelname = self._ctx.models_prefix + "New" + modelname

            w.write_line(
                """var item {full_modelname}
                if r.Body != nil {{
                    body, readError := ioutil.ReadAll(r.Body)
                    if body != nil {{
                        item = {new_modelname}()
                        err := item.FromJson(string(body))
                        if err != nil {{
                            ctrl.{rsp_400_error}(w, err)
                            return
                        }}
                    }} else {{
                        ctrl.{rsp_400_error}(w, readError)
                        return
                    }}
                }} else {{
                    bodyError := errors.New(\"Request do not have any body\")
                    ctrl.{rsp_500_error}(w, bodyError)
                    return
                }}
                result := ctrl.handler.{operation_name}(item, r)""".format(
                    full_modelname=full_modelname,
                    new_modelname=new_modelname,
                    rsp_400_error=rsp_400_error,
                    rsp_500_error=rsp_500_error,
                    operation_name=route.operation_name
                )
            )
        else:
            w.write_line(
                "result := ctrl.handler.{name}(r)".format(
                    name=route.operation_name
                )
            )

        error_responses = []
        for response in route.responses:
            if int(response.response_value) in rsp_errors:
                error_responses.append(response)

            # no response content defined, return as 'any'
            if response.has_json:
                write_method = "WriteJSONResponse"
            elif response.has_binary:
                write_method = "WriteByteResponse"
            else:
                write_method = "WriteAnyResponse"

            # This is require as workaround of https://github.com/open-traffic-generator/openapiart/issues/220
            if self._need_warning_check(route, response):
                rsp_section = """data, err := {mrl_name}MrlOpts.Marshal(result.StatusCode200().Msg())
                        if err != nil {{
                            ctrl.{rsp_400_error}(w, err)
                        }}
                        httpapi.WriteCustomJSONResponse(w, 200, data)
                    """.format(
                    mrl_name=util.camel_case(ctrl.yamlname),
                    rsp_400_error=rsp_400_error
                )
            else:
                rsp_section = """if _, err := httpapi.{write_method}(w, {response_value}, result.StatusCode{response_value}()); err != nil {{
                            log.Print(err.Error())
                    }}""".format(
                    write_method=write_method,
                    response_value=response.response_value
                )

            w.write_line("""if result.HasStatusCode{response_value}() {{
                               {rsp_section}
                               return
                           }}""".format(
                response_value=response.response_value,
                rsp_section=rsp_section
            ))
        w.write_line("ctrl.{rsp_500_error}(w, errors.New(\"Unknown error\"))".format(
            rsp_500_error=rsp_500_error
        ))
        w.pop_indent()
        w.write_line(
            "}",
            ""
        )

        for err_rsp in error_responses:
            schema = parse("$..schema").find(err_rsp.response_obj)[0].value
            if '$ref' in schema:
                schema = self._ctx.get_object_from_ref(schema["$ref"])
            for prop_name, prop_value in schema["properties"].items():
                break
            prop_type = prop_value["type"]
            if prop_type not in ["string", "array"]:
                raise Exception("Expecting Errors are string/ array of strings")
            if prop_type == "string":
                set_errors = """Set{prop_name}(rsp_err.Error())""".format(
                    prop_name=util.pascal_case(prop_name)
                )
            else:
                set_errors = """Set{prop_name}([]string{{rsp_err.Error()}})""".format(
                    prop_name=util.pascal_case(prop_name)
                )
            w.write_line("""func (ctrl *{struct_name}) {method_name}(w http.ResponseWriter, rsp_err error) {{
                result := {models_prefix}New{response_model_name}()
                result.StatusCode{response_value}().{set_errors}
                if _, err := httpapi.WriteJSONResponse(w, {response_value}, result.StatusCode{response_value}()); err != nil {{
                    log.Print(err.Error())
                }}
            }}
            """.format(
                struct_name=self._struct_name(ctrl),
                method_name=rsp_400_error if int(err_rsp.response_value) == 400 else rsp_500_error,
                models_prefix=self._ctx.models_prefix,
                response_model_name=route.response_model_name,
                response_value=err_rsp.response_value,
                set_errors=set_errors,
            ))

    def _need_warning_check(self, route, response):
        parse_schema = parse("$..schema").find(response.response_obj)
        schema = [s.value for s in parse_schema]
        if len(schema) == 0:
            return False
        schema = schema[0]
        if "$ref" in schema:
            schema = self._ctx.get_object_from_ref(schema["$ref"])
        parse_warnings = parse("$..warnings").find(schema)
        if route.method in ["PUT", "POST"] and \
                int(response.response_value) == 200 and \
                response.has_json and \
                len(parse_warnings) > 0:
            self._has_warning_check = True
            return True
        return False



    # def _write_servicehandler_interface(self, w: Writer, ctrl: ctx.Controller):
    #     w.write_line(
    #         f"type {ctrl.service_handler_name} interface {{",
    #     )
    #     w.push_indent()
    #     w.write_line(
    #         f"GetController() {ctrl.controller_name}",
    #     )
    #     for r in ctrl.routes:
    #         response_model_name = r.operation_name + 'Response'
    #         w.write_line(
    #             f"{r.operation_name}(r *http.Request) models.{response_model_name}",
    #         )
    #     w.pop_indent()
    #     w.write_line(
    #         "}",
    #         ""
    #     )
    #     pass


